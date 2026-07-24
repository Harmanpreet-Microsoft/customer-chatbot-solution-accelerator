#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Builds chat-app and scenario-app container images inside Azure Container
# Registry using `az acr build`, then updates the four App Services to run
# those images.
#
# Values are pulled from the current `azd` environment when available, with
# fallback to the last ARM deployment in the resource group. Any value can be
# overridden on the command line.
#
# Usage:
#   ./infra/scripts/post-provision/build_push_images.sh [options]
#
# Options:
#   --resource-group <name>           Azure resource group
#   --acr-name <name>                 ACR name (without .azurecr.io)
#   --chat-backend-app <name>         Chat backend App Service name
#   --chat-frontend-app <name>        Chat frontend App Service name
#   --scenario-backend-app <name>     Scenario backend App Service name
#   --scenario-frontend-app <name>    Scenario frontend App Service name
#   --image-tag <tag>                 Image tag (defaults to UTC timestamp)
#   --chat-backend-image <name>       Chat backend repository name (default: chat-backend)
#   --chat-frontend-image <name>      Chat frontend repository name (default: chat-frontend)
#   --scenario-backend-image <name>   Scenario backend repository name (default: scenario-backend)
#   --scenario-frontend-image <name>  Scenario frontend repository name (default: scenario-frontend)
#   --skip-chat-backend               Skip chat backend build/deploy
#   --skip-chat-frontend              Skip chat frontend build/deploy
#   --skip-scenario-backend           Skip scenario backend build/deploy
#   --skip-scenario-frontend          Skip scenario frontend build/deploy
#   --show-logs                       Stream full ACR build logs (default: quiet, only dump logs on failure)
#   -h, --help                        Show this help
# ---------------------------------------------------------------------------
set -euo pipefail

RESOURCE_GROUP=""
ACR_NAME=""
CHAT_BACKEND_APP=""
CHAT_FRONTEND_APP=""
SCENARIO_BACKEND_APP=""
SCENARIO_FRONTEND_APP=""
IMAGE_TAG=""
CHAT_BACKEND_IMAGE="chat-backend"
CHAT_FRONTEND_IMAGE="chat-frontend"
SCENARIO_BACKEND_IMAGE="scenario-backend"
SCENARIO_FRONTEND_IMAGE="scenario-frontend"
SKIP_CHAT_BACKEND=false
SKIP_CHAT_FRONTEND=false
SKIP_SCENARIO_BACKEND=false
SKIP_SCENARIO_FRONTEND=false
SHOW_LOGS=false

# ACR public-access state (populated by enable_acr_public_access)
ORIGINAL_ACR_PUBLIC_ACCESS=""
ORIGINAL_ACR_DEFAULT_ACTION=""
ACR_ACCESS_MODIFIED=false

usage() {
    sed -n '2,32p' "$0"
    exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --resource-group)          RESOURCE_GROUP="$2"; shift 2 ;;
        --acr-name)                ACR_NAME="$2"; shift 2 ;;
        --chat-backend-app)        CHAT_BACKEND_APP="$2"; shift 2 ;;
        --chat-frontend-app)       CHAT_FRONTEND_APP="$2"; shift 2 ;;
        --scenario-backend-app)    SCENARIO_BACKEND_APP="$2"; shift 2 ;;
        --scenario-frontend-app)   SCENARIO_FRONTEND_APP="$2"; shift 2 ;;
        --image-tag)               IMAGE_TAG="$2"; shift 2 ;;
        --chat-backend-image)      CHAT_BACKEND_IMAGE="$2"; shift 2 ;;
        --chat-frontend-image)     CHAT_FRONTEND_IMAGE="$2"; shift 2 ;;
        --scenario-backend-image)  SCENARIO_BACKEND_IMAGE="$2"; shift 2 ;;
        --scenario-frontend-image) SCENARIO_FRONTEND_IMAGE="$2"; shift 2 ;;
        --skip-chat-backend)       SKIP_CHAT_BACKEND=true; shift ;;
        --skip-chat-frontend)      SKIP_CHAT_FRONTEND=true; shift ;;
        --skip-scenario-backend)   SKIP_SCENARIO_BACKEND=true; shift ;;
        --skip-scenario-frontend)  SKIP_SCENARIO_FRONTEND=true; shift ;;
        --show-logs)               SHOW_LOGS=true; shift ;;
        -h|--help)                 usage 0 ;;
        *) echo "Unknown option: $1" >&2; usage 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Build contexts and Dockerfiles
CHAT_BACKEND_CTX="$REPO_ROOT"
CHAT_BACKEND_DOCKERFILE="$REPO_ROOT/chat-app/backend/Dockerfile"
CHAT_FRONTEND_CTX="$REPO_ROOT/chat-app/frontend"
SCENARIO_BACKEND_CTX="$REPO_ROOT/scenario-app/backend"
SCENARIO_FRONTEND_CTX="$REPO_ROOT"
SCENARIO_FRONTEND_DOCKERFILE="$REPO_ROOT/scenario-app/frontend/Dockerfile"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
command -v az >/dev/null 2>&1 || { echo "ERROR: Azure CLI ('az') is required." >&2; exit 1; }

if ! az account show --only-show-errors >/dev/null 2>&1; then
    echo "ERROR: You are not signed in to the Azure CLI. Run 'az login' (or 'az login --use-device-code' in restricted environments) and try again." >&2
    exit 1
fi

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
    local registry="$1" image="$2" tag="$3" context="$4" dockerfile="${5:-}"
    echo ""
    echo ">>> Building ${registry}.azurecr.io/${image}:${tag}"

    if $SHOW_LOGS; then
        if [[ -n "$dockerfile" ]]; then
            az acr build \
                --registry "$registry" \
                --image "${image}:${tag}" \
                --image "${image}:latest" \
                --only-show-errors \
                --file "$dockerfile" \
                "$context"
        else
            az acr build \
                --registry "$registry" \
                --image "${image}:${tag}" \
                --image "${image}:latest" \
                --only-show-errors \
                "$context"
        fi
        return
    fi

    echo "    (streaming logs suppressed; pass --show-logs to see full output)"
    local out exit_code=0 run_id=""
    set +e
    if [[ -n "$dockerfile" ]]; then
        out="$(az acr build \
            --registry "$registry" \
            --image "${image}:${tag}" \
            --image "${image}:latest" \
            --no-logs \
            --only-show-errors \
            -o json \
            --file "$dockerfile" \
            "$context" 2>&1)"
    else
        out="$(az acr build \
            --registry "$registry" \
            --image "${image}:${tag}" \
            --image "${image}:latest" \
            --no-logs \
            --only-show-errors \
            -o json \
            "$context" 2>&1)"
    fi
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

enable_acr_public_access() {
    local name="$1"
    echo "Checking ACR public network access for '$name'..."

    local raw_public_access raw_default_action
    raw_public_access="$(az acr show --name "$name" --query "publicNetworkAccess" -o tsv 2>/dev/null)" || {
        echo "ERROR: Failed to read ACR public network access for '$name'. Ensure the registry exists and you have sufficient permissions." >&2
        return 1
    }
    if [[ -z "$raw_public_access" ]]; then
        echo "ERROR: ACR '$name' returned no publicNetworkAccess value. Ensure the registry name is correct." >&2
        return 1
    fi
    ORIGINAL_ACR_PUBLIC_ACCESS="$raw_public_access"

    raw_default_action="$(az acr show --name "$name" --query "networkRuleSet.defaultAction" -o tsv 2>/dev/null)" || {
        echo "ERROR: Failed to read ACR network rule set for '$name'." >&2
        return 1
    }
    ORIGINAL_ACR_DEFAULT_ACTION="$raw_default_action"
    echo "  Current: publicNetworkAccess=${ORIGINAL_ACR_PUBLIC_ACCESS}  defaultAction=${ORIGINAL_ACR_DEFAULT_ACTION}"

    if [[ "$ORIGINAL_ACR_PUBLIC_ACCESS" != "Enabled" ]]; then
        echo "  Enabling ACR public network access..."
        az acr update --name "$name" --public-network-enabled true --only-show-errors >/dev/null
        ACR_ACCESS_MODIFIED=true
    fi

    if [[ "$ORIGINAL_ACR_DEFAULT_ACTION" == "Deny" ]]; then
        echo "  Setting ACR network default action to Allow..."
        az acr update --name "$name" --default-action Allow --only-show-errors >/dev/null
        ACR_ACCESS_MODIFIED=true
    fi

    if $ACR_ACCESS_MODIFIED; then
        echo "  ACR network access updated. Waiting 15 s for changes to propagate..."
        sleep 15
    else
        echo "  ACR public access already open - no changes needed."
    fi
    echo ""
}

restore_acr_access() {
    local name="$1"
    echo ""
    echo "=== Restoring original ACR network settings ==="
    if ! $ACR_ACCESS_MODIFIED; then
        echo "  ACR unchanged - no restoration needed."
        return 0
    fi
    echo "  Restoring ACR '$name' to original settings..."
    local update_args=("acr" "update" "--name" "$name" "--only-show-errors")
    if [[ "$ORIGINAL_ACR_PUBLIC_ACCESS" != "Enabled" ]]; then
        update_args+=("--public-network-enabled" "false")
    fi
    if [[ "$ORIGINAL_ACR_DEFAULT_ACTION" == "Deny" ]]; then
        update_args+=("--default-action" "Deny")
    fi
    if az "${update_args[@]}" >/dev/null 2>&1; then
        echo "  ACR settings restored (publicNetworkAccess=${ORIGINAL_ACR_PUBLIC_ACCESS}, defaultAction=${ORIGINAL_ACR_DEFAULT_ACTION})."
    else
        echo "  WARNING: Failed to restore ACR network settings for '$name'. Please restore manually."
        echo "    Expected: publicNetworkAccess=${ORIGINAL_ACR_PUBLIC_ACCESS}  defaultAction=${ORIGINAL_ACR_DEFAULT_ACTION}"
    fi
}

cleanup_on_exit() {
    restore_acr_access "$ACR_NAME"
}

# ---------------------------------------------------------------------------
# Resolve inputs
# ---------------------------------------------------------------------------
[[ -z "$RESOURCE_GROUP" ]]        && RESOURCE_GROUP="$(azd_get AZURE_RESOURCE_GROUP)"
[[ -z "$ACR_NAME" ]]              && ACR_NAME="$(azd_get AZURE_CONTAINER_REGISTRY_NAME)"
[[ -z "$ACR_NAME" ]]              && ACR_NAME="$(azd_get ACR_NAME)"
[[ -z "$CHAT_BACKEND_APP" ]]      && CHAT_BACKEND_APP="$(azd_get CHAT_API_APP_NAME)"
[[ -z "$CHAT_FRONTEND_APP" ]]     && CHAT_FRONTEND_APP="$(azd_get CHAT_WEB_APP_NAME)"
[[ -z "$SCENARIO_BACKEND_APP" ]]  && SCENARIO_BACKEND_APP="$(azd_get SCENARIO_API_APP_NAME)"
[[ -z "$SCENARIO_FRONTEND_APP" ]] && SCENARIO_FRONTEND_APP="$(azd_get SCENARIO_WEB_APP_NAME)"
[[ -z "$IMAGE_TAG" ]]             && IMAGE_TAG="$(azd_get AZURE_ENV_IMAGETAG)"

if [[ -z "$ACR_NAME" || -z "$CHAT_BACKEND_APP" || -z "$CHAT_FRONTEND_APP" || -z "$SCENARIO_BACKEND_APP" || -z "$SCENARIO_FRONTEND_APP" ]]; then
    [[ -z "$RESOURCE_GROUP" ]] && { echo "ERROR: --resource-group required (or run inside an azd env)." >&2; exit 1; }
    echo "Fetching deployment outputs from '$RESOURCE_GROUP'..."
    OUTPUTS_JSON="$(fetch_deployment_outputs "$RESOURCE_GROUP")"
    if [[ -n "$OUTPUTS_JSON" ]]; then
        [[ -z "$ACR_NAME" ]]              && ACR_NAME="$(extract_output "$OUTPUTS_JSON" AZURE_CONTAINER_REGISTRY_NAME azureContainerRegistryName ACR_NAME acrName)"
        [[ -z "$CHAT_BACKEND_APP" ]]      && CHAT_BACKEND_APP="$(extract_output "$OUTPUTS_JSON" CHAT_API_APP_NAME chatApiAppName)"
        [[ -z "$CHAT_FRONTEND_APP" ]]     && CHAT_FRONTEND_APP="$(extract_output "$OUTPUTS_JSON" CHAT_WEB_APP_NAME chatWebAppName)"
        [[ -z "$SCENARIO_BACKEND_APP" ]]  && SCENARIO_BACKEND_APP="$(extract_output "$OUTPUTS_JSON" SCENARIO_API_APP_NAME scenarioApiAppName)"
        [[ -z "$SCENARIO_FRONTEND_APP" ]] && SCENARIO_FRONTEND_APP="$(extract_output "$OUTPUTS_JSON" SCENARIO_WEB_APP_NAME scenarioWebAppName)"
    fi
fi

[[ -z "$IMAGE_TAG" ]] && IMAGE_TAG="$(date -u +%Y%m%d%H%M%S)"

[[ -z "$RESOURCE_GROUP" ]] && { echo "ERROR: Missing resource group." >&2; exit 1; }
[[ -z "$ACR_NAME"       ]] && { echo "ERROR: Missing ACR name." >&2; exit 1; }
$SKIP_CHAT_BACKEND     || [[ -n "$CHAT_BACKEND_APP" ]]     || { echo "ERROR: Missing chat backend app name."     >&2; exit 1; }
$SKIP_CHAT_FRONTEND    || [[ -n "$CHAT_FRONTEND_APP" ]]    || { echo "ERROR: Missing chat frontend app name."    >&2; exit 1; }
$SKIP_SCENARIO_BACKEND  || [[ -n "$SCENARIO_BACKEND_APP" ]]  || { echo "ERROR: Missing scenario backend app name."  >&2; exit 1; }
$SKIP_SCENARIO_FRONTEND || [[ -n "$SCENARIO_FRONTEND_APP" ]] || { echo "ERROR: Missing scenario frontend app name." >&2; exit 1; }

ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"

cat <<EOF

Configuration
  Resource group         : $RESOURCE_GROUP
  ACR                    : $ACR_LOGIN_SERVER
  Chat backend app       : $CHAT_BACKEND_APP
  Chat frontend app      : $CHAT_FRONTEND_APP
  Scenario backend app   : $SCENARIO_BACKEND_APP
  Scenario frontend app  : $SCENARIO_FRONTEND_APP
  Image tag              : $IMAGE_TAG
EOF

trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo ""
enable_acr_public_access "$ACR_NAME"

# ---------------------------------------------------------------------------
# Build & deploy
# ---------------------------------------------------------------------------
if ! $SKIP_CHAT_BACKEND; then
    [[ -f "$CHAT_BACKEND_DOCKERFILE" ]] || { echo "ERROR: $CHAT_BACKEND_DOCKERFILE not found." >&2; exit 1; }
    run_acr_build "$ACR_NAME" "$CHAT_BACKEND_IMAGE"  "$IMAGE_TAG" "$CHAT_BACKEND_CTX"  "$CHAT_BACKEND_DOCKERFILE"
    update_webapp "$RESOURCE_GROUP" "$CHAT_BACKEND_APP"  "$ACR_LOGIN_SERVER" "$CHAT_BACKEND_IMAGE"  "$IMAGE_TAG"
else
    echo "Skipping chat backend (--skip-chat-backend)."
fi

echo ""

if ! $SKIP_CHAT_FRONTEND; then
    [[ -f "$CHAT_FRONTEND_CTX/Dockerfile" ]] || { echo "ERROR: $CHAT_FRONTEND_CTX/Dockerfile not found." >&2; exit 1; }
    run_acr_build "$ACR_NAME" "$CHAT_FRONTEND_IMAGE" "$IMAGE_TAG" "$CHAT_FRONTEND_CTX"
    update_webapp "$RESOURCE_GROUP" "$CHAT_FRONTEND_APP" "$ACR_LOGIN_SERVER" "$CHAT_FRONTEND_IMAGE" "$IMAGE_TAG"
else
    echo "Skipping chat frontend (--skip-chat-frontend)."
fi

echo ""

if ! $SKIP_SCENARIO_BACKEND; then
    [[ -f "$SCENARIO_BACKEND_CTX/Dockerfile" ]] || { echo "ERROR: $SCENARIO_BACKEND_CTX/Dockerfile not found." >&2; exit 1; }
    run_acr_build "$ACR_NAME" "$SCENARIO_BACKEND_IMAGE"  "$IMAGE_TAG" "$SCENARIO_BACKEND_CTX"
    update_webapp "$RESOURCE_GROUP" "$SCENARIO_BACKEND_APP"  "$ACR_LOGIN_SERVER" "$SCENARIO_BACKEND_IMAGE"  "$IMAGE_TAG"
else
    echo "Skipping scenario backend (--skip-scenario-backend)."
fi

echo ""

if ! $SKIP_SCENARIO_FRONTEND; then
    [[ -f "$SCENARIO_FRONTEND_DOCKERFILE" ]] || { echo "ERROR: $SCENARIO_FRONTEND_DOCKERFILE not found." >&2; exit 1; }
    run_acr_build "$ACR_NAME" "$SCENARIO_FRONTEND_IMAGE" "$IMAGE_TAG" "$SCENARIO_FRONTEND_CTX" "$SCENARIO_FRONTEND_DOCKERFILE"
    update_webapp "$RESOURCE_GROUP" "$SCENARIO_FRONTEND_APP" "$ACR_LOGIN_SERVER" "$SCENARIO_FRONTEND_IMAGE" "$IMAGE_TAG"
else
    echo "Skipping scenario frontend (--skip-scenario-frontend)."
fi

echo ""
echo "Done. Images published with tag '$IMAGE_TAG'."
echo ""
