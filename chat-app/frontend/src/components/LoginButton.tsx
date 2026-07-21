import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import {
  Menu,
  MenuDivider,
  MenuItem,
  MenuList,
  MenuPopover,
  MenuTrigger,
} from '@fluentui/react-components';
import { Person20Regular, SignOut20Regular } from '@fluentui/react-icons';
import { ShieldWarning, Spinner } from '@phosphor-icons/react';

type LoginButtonProps = {
  showGuestActions?: boolean;
  compact?: boolean;
};

export function LoginButton({ showGuestActions = true, compact = false }: LoginButtonProps) {
  const { user, isLoading, login, logout, isAuthenticated, isIdentityProviderConfigured } = useAuth();

  if (isLoading) {
    return (
      <Button variant="outline" size="sm" disabled className="transition-all duration-200">
        <Spinner className="w-5 h-5 animate-spin" />
      </Button>
    );
  }

  if (isAuthenticated && user) {
    let initials = "U";

    if (user.name && user.name.includes("@")) {
      const emailPrefix = user.name.split("@")[0];
      const parts = emailPrefix.split(".");
      if (parts.length >= 2) {
        initials = (parts[0][0] + parts[1][0]).toUpperCase();
      } else {
        initials = emailPrefix.substring(0, 2).toUpperCase();
      }
    } else if (user.name) {
      initials = user.name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
    }

    return (
      <div className="flex items-center gap-2">
        <Menu>
          <MenuTrigger>
            <Button
              variant="ghost"
              size="sm"
              className="transition-all duration-200 hover:bg-accent p-1"
              title={user.email}
            >
              <Avatar className={compact ? 'w-7 h-7' : 'w-8 h-8'}>
                <AvatarImage src={undefined} alt={user.name} />
                <AvatarFallback className="bg-primary text-primary-foreground text-sm">
                  {initials}
                </AvatarFallback>
              </Avatar>
            </Button>
          </MenuTrigger>
          <MenuPopover>
            <MenuList>
              <MenuItem icon={<Person20Regular />} disabled style={{ cursor: 'default' }}>
                <div className="flex flex-col min-w-0 max-w-[220px]">
                  <span className="font-semibold text-sm truncate block">{user.name}</span>
                  <span className="text-xs text-gray-500 truncate block">{user.email}</span>
                </div>
              </MenuItem>
              <MenuDivider />
              <MenuItem icon={<SignOut20Regular />} onClick={logout}>
                Logout
              </MenuItem>
            </MenuList>
          </MenuPopover>
        </Menu>
      </div>
    );
  }

  if (!isIdentityProviderConfigured) {
    return (
      <Button
        variant="outline"
        size="sm"
        disabled
        className="transition-all duration-200 flex items-center gap-2 opacity-50 cursor-not-allowed"
        title="Enable Identity Provider in Azure Portal to enable authentication"
      >
        <ShieldWarning className="w-5 h-5" />
        {!compact && <span className="hidden sm:inline text-xs">Enable Identity Provider</span>}
      </Button>
    );
  }

  if (showGuestActions) {
    return (
      <Button
        variant="default"
        size="sm"
        onClick={login}
        className="transition-all duration-200 flex items-center gap-2"
        title="Sign in with Microsoft"
      >
        <ShieldWarning className="w-5 h-5" />
        {!compact && <span className="text-xs">Login</span>}
      </Button>
    );
  }

  return null;
}
