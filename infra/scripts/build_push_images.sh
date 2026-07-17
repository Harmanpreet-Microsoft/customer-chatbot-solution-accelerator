#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Builds the backend (src/api) and frontend (src/App) container images inside
# Azure Container Registry using `az acr build`, then updates the two App
# Services (api-<suffix> and app-<suffix>) to run those images.
#
# Values are pulled from the current `azd` environment when available, with
# fallback to the last ARM deployment in the resource group. Any value can be
# overridden on the command line.
#
# Usage:
#   ./build_push_images.sh [options]
#
# Options:
#   --resource-group <name>     Azure resource group
#   --acr-name <name>           ACR name (without .azurecr.io)
#   --backend-app <name>        Backend App Service name (api-<suffix>)
#   --frontend-app <name>       Frontend App Service name (app-<suffix>)
#   --image-tag <tag>           Image tag (defaults to UTC timestamp)
#   --backend-image <name>      Backend repository name (default: backend)
#   --frontend-image <name>     Frontend repository name (default: frontend)
#   --skip-backend              Skip backend build/deploy
#   --skip-frontend             Skip frontend build/deploy
#   --show-logs                 Stream full ACR build logs (default: quiet, only dump logs on failure)
#   -h, --help                  Show this help
# ---------------------------------------------------------------------------
set -euo pipefail

RESOURCE_GROUP=""
ACR_NAME=""
BACKEND_APP=""
FRONTEND_APP=""
IMAGE_TAG=""
BACKEND_IMAGE="backend"
FRONTEND_IMAGE="frontend"
SKIP_BACKEND=false
SKIP_FRONTEND=false
SHOW_LOGS=false

usage() {
    sed -n '2,25p' "$0"
    exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --resource-group)  RESOURCE_GROUP="$2"; shift 2 ;;
        --acr-name)        ACR_NAME="$2"; shift 2 ;;
        --backend-app)     BACKEND_APP="$2"; shift 2 ;;
        --frontend-app)    FRONTEND_APP="$2"; shift 2 ;;
        --image-tag)       IMAGE_TAG="$2"; shift 2 ;;
        --backend-image)   BACKEND_IMAGE="$2"; shift 2 ;;
        --frontend-image)  FRONTEND_IMAGE="$2"; shift 2 ;;
        --skip-backend)    SKIP_BACKEND=true; shift ;;
        --skip-frontend)   SKIP_FRONTEND=true; shift ;;
        --show-logs)       SHOW_LOGS=true; shift ;;
        -h|--help)         usage 0 ;;
        *) echo "Unknown option: $1" >&2; usage 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_CTX="$REPO_ROOT/src/api"
FRONTEND_CTX="$REPO_ROOT/src/App"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
command -v az >/dev/null 2>&1 || { echo "ERROR: Azure CLI ('az') is required." >&2; exit 1; }

azd_available() { command -v azd >/dev/null 2>&1; }

azd_get() {
    local key="$1" value=""
    azd_available || return 0
    # A missing key makes azd exit non-zero (and may print an error to stdout);
    # treat that as "not set" so callers fall back to their defaults.
    value="$(azd env get-value "$key" 2>/dev/null)" || return 0
    case "$value" in
        *ERROR:*|*"not found in environment"*) return 0 ;;
    esac
    printf '%s' "$value"
}

# Extract a top-level output value from `az deployment group show` JSON. Uses
# case-insensitive key match and tolerates absence of jq (falls back to grep).
extract_output() {
    local json="$1"; shift
    local key
    for key in "$@"; do
        local val=""
        if command -v jq >/dev/null 2>&1; then
            val="$(echo "$json" | jq -r --arg k "$key" '
                to_entries
                | map(select(.key | ascii_downcase == ($k | ascii_downcase)))
                | .[0].value.value // empty')"
        else
            val="$(echo "$json" | grep -i -A 3 "\"$key\"" | grep '"value"' | sed 's/.*"value": *"\([^"]*\)".*/\1/' | head -1)"
        fi
        val="$(echo -n "$val" | xargs || true)"
        if [[ -n "$val" ]]; then
            printf '%s' "$val"
            return 0
        fi
    done
}

fetch_deployment_outputs() {
    local rg="$1"
    local dep
    dep="$(az group show --name "$rg" --query 'tags.DeploymentName' -o tsv 2>/dev/null || true)"
    if [[ -z "$dep" ]]; then
        dep="$(az deployment group list --resource-group "$rg" --query '[0].name' -o tsv 2>/dev/null || true)"
    fi
    [[ -z "$dep" ]] && return 0
    az deployment group show --resource-group "$rg" --name "$dep" --query 'properties.outputs' -o json 2>/dev/null || true
}

run_acr_build() {
    local registry="$1" image="$2" tag="$3" context="$4"
    echo ""
    echo ">>> Building ${registry}.azurecr.io/${image}:${tag}"

    if $SHOW_LOGS; then
        az acr build \
            --registry "$registry" \
            --image "${image}:${tag}" \
            --image "${image}:latest" \
            --only-show-errors \
            "$context"
        return
    fi

    echo "    (streaming logs suppressed; pass --show-logs to see full output)"
    local out exit_code=0 run_id=""
    set +e
    out="$(az acr build \
        --registry "$registry" \
        --image "${image}:${tag}" \
        --image "${image}:latest" \
        --no-logs \
        --only-show-errors \
        -o json \
        "$context" 2>&1)"
    exit_code=$?
    set -e

    if command -v jq >/dev/null 2>&1; then
        run_id="$(printf '%s' "$out" | jq -r '.runId // empty' 2>/dev/null || true)"
    else
        run_id="$(printf '%s' "$out" | grep -oE '"runId":[[:space:]]*"[^"]+"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')"
    fi
    # On failure the CLI does not emit JSON, only:
    #   ERROR: The run with ID 'caXX' finished with unsuccessful status ...
    if [[ -z "$run_id" ]]; then
        run_id="$(printf '%s' "$out" | grep -oE "run with ID '[^']+'" | head -1 | sed "s/.*'\([^']*\)'.*/\1/")"
    fi

    if [[ $exit_code -ne 0 ]]; then
        if [[ -n "$run_id" ]]; then
            echo ""
            echo "Build failed (runId: $run_id). Fetching logs..." >&2
            az acr task logs --registry "$registry" --run-id "$run_id" --only-show-errors || true
        else
            printf '%s\n' "$out" >&2
        fi
        echo "ERROR: az acr build failed for image $image" >&2
        return $exit_code
    fi

    if [[ -n "$run_id" ]]; then
        echo "    Succeeded (runId: $run_id)"
    fi
}

update_webapp() {
    local rg="$1" app="$2" login_server="$3" image="$4" tag="$5"
    local full="${login_server}/${image}:${tag}"
    echo ""
    echo ">>> Updating web app '$app' -> $full"
    az webapp config container set \
        --name "$app" \
        --resource-group "$rg" \
        --container-image-name "$full" \
        --only-show-errors >/dev/null

    echo ">>> Restarting '$app'..."
    az webapp restart --name "$app" --resource-group "$rg" --only-show-errors >/dev/null
}

# ---------------------------------------------------------------------------
# Resolve inputs
# ---------------------------------------------------------------------------
[[ -z "$RESOURCE_GROUP" ]] && RESOURCE_GROUP="$(azd_get AZURE_RESOURCE_GROUP)"
[[ -z "$ACR_NAME"       ]] && ACR_NAME="$(azd_get AZURE_CONTAINER_REGISTRY_NAME)"
[[ -z "$ACR_NAME"       ]] && ACR_NAME="$(azd_get ACR_NAME)"
[[ -z "$BACKEND_APP"    ]] && BACKEND_APP="$(azd_get API_APP_NAME)"
SOLUTION_SUFFIX="$(azd_get SOLUTION_NAME)"
[[ -z "$FRONTEND_APP" && -n "$SOLUTION_SUFFIX" ]] && FRONTEND_APP="app-${SOLUTION_SUFFIX}"
[[ -z "$IMAGE_TAG"      ]] && IMAGE_TAG="$(azd_get AZURE_ENV_IMAGETAG)"

if [[ -z "$ACR_NAME" || -z "$BACKEND_APP" || -z "$FRONTEND_APP" ]]; then
    [[ -z "$RESOURCE_GROUP" ]] && { echo "ERROR: --resource-group required (or run inside an azd env)." >&2; exit 1; }
    echo "Fetching deployment outputs from '$RESOURCE_GROUP'..."
    OUTPUTS_JSON="$(fetch_deployment_outputs "$RESOURCE_GROUP")"
    if [[ -n "$OUTPUTS_JSON" ]]; then
        [[ -z "$ACR_NAME"    ]] && ACR_NAME="$(extract_output "$OUTPUTS_JSON" AZURE_CONTAINER_REGISTRY_NAME azureContainerRegistryName ACR_NAME acrName)"
        [[ -z "$BACKEND_APP" ]] && BACKEND_APP="$(extract_output "$OUTPUTS_JSON" API_APP_NAME apiAppName)"
        if [[ -z "$SOLUTION_SUFFIX" ]]; then
            SOLUTION_SUFFIX="$(extract_output "$OUTPUTS_JSON" SOLUTION_NAME solutionName)"
        fi
        [[ -z "$FRONTEND_APP" && -n "$SOLUTION_SUFFIX" ]] && FRONTEND_APP="app-${SOLUTION_SUFFIX}"
    fi
fi

[[ -z "$IMAGE_TAG" ]] && IMAGE_TAG="$(date -u +%Y%m%d%H%M%S)"

[[ -z "$RESOURCE_GROUP" ]] && { echo "ERROR: Missing resource group." >&2; exit 1; }
[[ -z "$ACR_NAME"       ]] && { echo "ERROR: Missing ACR name." >&2; exit 1; }
$SKIP_BACKEND  || [[ -n "$BACKEND_APP"  ]] || { echo "ERROR: Missing backend app name."  >&2; exit 1; }
$SKIP_FRONTEND || [[ -n "$FRONTEND_APP" ]] || { echo "ERROR: Missing frontend app name." >&2; exit 1; }

ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"

cat <<EOF

Configuration
  Resource group : $RESOURCE_GROUP
  ACR            : $ACR_LOGIN_SERVER
  Backend app    : $BACKEND_APP
  Frontend app   : $FRONTEND_APP
  Image tag      : $IMAGE_TAG
EOF

# ---------------------------------------------------------------------------
# Build & deploy
# ---------------------------------------------------------------------------
if ! $SKIP_BACKEND; then
    [[ -f "$BACKEND_CTX/Dockerfile" ]] || { echo "ERROR: $BACKEND_CTX/Dockerfile not found." >&2; exit 1; }
    run_acr_build "$ACR_NAME" "$BACKEND_IMAGE"  "$IMAGE_TAG" "$BACKEND_CTX"
    update_webapp "$RESOURCE_GROUP" "$BACKEND_APP"  "$ACR_LOGIN_SERVER" "$BACKEND_IMAGE"  "$IMAGE_TAG"
else
    echo "Skipping backend (--skip-backend)."
fi

if ! $SKIP_FRONTEND; then
    [[ -f "$FRONTEND_CTX/Dockerfile" ]] || { echo "ERROR: $FRONTEND_CTX/Dockerfile not found." >&2; exit 1; }
    run_acr_build "$ACR_NAME" "$FRONTEND_IMAGE" "$IMAGE_TAG" "$FRONTEND_CTX"
    update_webapp "$RESOURCE_GROUP" "$FRONTEND_APP" "$ACR_LOGIN_SERVER" "$FRONTEND_IMAGE" "$IMAGE_TAG"
else
    echo "Skipping frontend (--skip-frontend)."
fi

echo ""
echo "Done. Images published with tag '$IMAGE_TAG'."
