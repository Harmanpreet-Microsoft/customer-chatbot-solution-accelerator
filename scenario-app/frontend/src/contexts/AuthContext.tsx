import { api, setEasyAuthHeaders } from '@/lib/api';
import { createContext, ReactNode, useContext, useEffect, useState } from 'react';

export interface User {
  id: string;
  name: string;
  email: string;
  roles: string[];
  is_authenticated: boolean;
  is_guest?: boolean;
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
  isAuthenticated: boolean;
  isIdentityProviderConfigured: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const AUTH_REDIRECT_KEY = 'ccsa_easyauth_redirect';

const CLAIM_TYPE_MAP: Record<string, string> = {
  'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress': 'email',
  'http://schemas.microsoft.com/identity/claims/objectidentifier': 'oid',
  'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier': 'nameidentifier',
  'preferred_username': 'preferred_username',
  'name': 'name',
  'sub': 'sub',
};

type EasyAuthProbe = {
  headers: Record<string, string> | null;
  providerConfigured: boolean;
  needsLoginRedirect: boolean;
};

function loginRedirectAlreadyAttempted(): boolean {
  try {
    return sessionStorage.getItem(AUTH_REDIRECT_KEY) === '1';
  } catch {
    return false;
  }
}

function markLoginRedirectAttempted(): void {
  try {
    sessionStorage.setItem(AUTH_REDIRECT_KEY, '1');
  } catch {
  }
}

function clearLoginRedirectAttempted(): void {
  try {
    sessionStorage.removeItem(AUTH_REDIRECT_KEY);
  } catch {
  }
}

async function probeEasyAuth(): Promise<EasyAuthProbe> {
  try {
    const response = await fetch('/.auth/me', {
      credentials: 'include',
      redirect: 'manual',
    });

    if (response.type === 'opaqueredirect') {
      return { headers: null, providerConfigured: true, needsLoginRedirect: true };
    }

    if (response.status === 401 || response.status === 403) {
      return { headers: null, providerConfigured: true, needsLoginRedirect: true };
    }

    if (!response.ok) {
      return { headers: null, providerConfigured: false, needsLoginRedirect: false };
    }

    const authData = await response.json();
    if (!authData?.length) {
      return { headers: null, providerConfigured: true, needsLoginRedirect: true };
    }

    const { user_claims: claims, provider_name, id_token } = authData[0];
    const claimsObject = claims.reduce((acc: Record<string, string>, { typ, val }: { typ: string; val: string }) => {
      acc[CLAIM_TYPE_MAP[typ] || typ.split('/').pop() || typ] = val;
      return acc;
    }, {});

    const principalId = (
      claimsObject.oid ||
      claimsObject.nameidentifier ||
      claimsObject.sub ||
      ''
    ).trim();

    if (!principalId) {
      return { headers: null, providerConfigured: true, needsLoginRedirect: true };
    }

    return {
      headers: {
        'x-ms-client-principal-id': principalId,
        'x-ms-client-principal-name': claimsObject.name || claimsObject.email || claimsObject.preferred_username,
        'x-ms-client-principal-idp': provider_name,
        'x-ms-token-aad-id-token': id_token,
        'x-ms-client-principal': btoa(JSON.stringify({ ...claimsObject, oid: principalId })),
      },
      providerConfigured: true,
      needsLoginRedirect: false,
    };
  } catch {
    return { headers: null, providerConfigured: false, needsLoginRedirect: false };
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isIdentityProviderConfigured, setIsIdentityProviderConfigured] = useState(false);

  const login = () => {
    markLoginRedirectAttempted();
    window.location.href = '/.auth/login/aad';
  };

  const logout = () => {
    setEasyAuthHeaders(null);
    clearLoginRedirectAttempted();
    window.location.href = '/.auth/logout';
  };

  useEffect(() => {
    let isAuthenticating = false;
    let isMounted = true;
    let retryCount = 0;
    let retryTimeoutId: ReturnType<typeof setTimeout> | null = null;
    const MAX_RETRIES = 3;
    const RETRY_DELAY = 1000;

    const finishLoading = () => {
      if (!isMounted) return;
      setIsLoading(false);
      isAuthenticating = false;
    };

    const initializeAuth = async (isRetry = false) => {
      if (isAuthenticating || !isMounted) return;

      isAuthenticating = true;
      if (!isRetry) retryCount = 0;

      let providerConfigured = false;
      try {
        const authProbe = await probeEasyAuth();
        providerConfigured = authProbe.providerConfigured;

        const easyAuthHeaders = authProbe.headers;
        if (easyAuthHeaders) {
          setEasyAuthHeaders(easyAuthHeaders);
          clearLoginRedirectAttempted();
        } else {
          setEasyAuthHeaders(null);
        }

        const response = await api.get('/api/auth/me');

        const principalId = easyAuthHeaders?.['x-ms-client-principal-id'];
        if (
          response.data.is_guest &&
          principalId &&
          retryCount < MAX_RETRIES
        ) {
          retryCount++;
          retryTimeoutId = setTimeout(() => {
            isAuthenticating = false;
            initializeAuth(true);
          }, RETRY_DELAY);
          return;
        }

        if (!isMounted) return;

        setUser(response.data);
        setIsIdentityProviderConfigured(
          providerConfigured ||
            !response.data.is_guest ||
            response.data.is_authenticated
        );
        finishLoading();
      } catch (error: any) {
        if (!isMounted) return;

        setIsIdentityProviderConfigured(
          providerConfigured || error.response?.status === 302
        );
        setUser(null);
        finishLoading();
      }
    };

    initializeAuth();

    const handleVisibilityChange = () => {
      if (!document.hidden) initializeAuth();
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      isMounted = false;
      if (retryTimeoutId) clearTimeout(retryTimeoutId);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  const value: AuthContextType = {
    user,
    isLoading,
    login,
    logout,
    isAuthenticated: !!user && !user.is_guest,
    isIdentityProviderConfigured,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
