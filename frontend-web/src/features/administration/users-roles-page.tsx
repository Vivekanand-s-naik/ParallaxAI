import * as React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  KeyRound,
  RefreshCw,
  Search,
  Shield,
  UserCheck,
  UserX,
  Users,
} from 'lucide-react';
import { queryKeys } from '@/app/query-client';
import { platformServices } from '@/services/platform-services';
import { PermissionGate } from '@/components/navigation/permission-guard';
import { PageHeader } from '@/components/common/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ErrorState } from '@/components/feedback/error-state';
import { LoadingSkeleton } from '@/components/feedback/loading-skeleton';
import { useUiStore } from '@/stores/ui-store';
import { normalizeApiError } from '@/services/api-error';
import { formatDateTime } from '@/lib/utils';

export function UsersAndRolesPage() {
  const queryClient = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);

  const [search, setSearch] = React.useState('');
  const [roleFilter, setRoleFilter] = React.useState('');

  const usersQuery = useQuery({
    queryKey: queryKeys.users.list({
      search: search.trim() || undefined,
      role: roleFilter || undefined,
    }),
    queryFn: () =>
      platformServices.listUsers({
        search: search.trim() || undefined,
        role: roleFilter || undefined,
      }),
  });

  const rolesQuery = useQuery({
    queryKey: queryKeys.roles.list(),
    queryFn: () => platformServices.listRoles(),
  });

  const permissionsQuery = useQuery({
    queryKey: queryKeys.roles.permissions(),
    queryFn: () => platformServices.listPermissions(),
  });

  const toggleStatusMutation = useMutation({
    mutationFn: ({
      userId,
      is_active,
    }: {
      userId: string;
      is_active: boolean;
    }) => platformServices.updateUserStatus(userId, { is_active }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
      addToast({
        title: 'Operator Status Updated',
        description: `${updated.email} is now ${
          updated.is_active ? 'active' : 'deactivated'
        }.`,
        variant: 'info',
      });
    },
    onError: (err) => {
      addToast({
        title: 'Status update rejected',
        description: normalizeApiError(err).message,
        variant: 'error',
      });
    },
  });

  const assignRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      platformServices.updateUserRoles(userId, { roles: [role] }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.roles.all });
      addToast({
        title: 'Role Assignment Updated',
        description: `${updated.email} assigned role ${updated.primary_role}.`,
        variant: 'success',
      });
    },
    onError: (err) => {
      addToast({
        title: 'Role assignment rejected',
        description: normalizeApiError(err).message,
        variant: 'error',
      });
    },
  });

  return (
    <div className="space-y-6" data-testid="users-roles-page">
      <PageHeader
        title="Identity, Users & RBAC Matrix"
        description="Manage operator accounts, assign enterprise governance roles, and inspect granular database-backed permission mappings."
        badge={
          <Badge variant="default">
            {usersQuery.data?.total ?? 0} Operators •{' '}
            {rolesQuery.data?.length ?? 0} Roles
          </Badge>
        }
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              usersQuery.refetch();
              rolesQuery.refetch();
            }}
          >
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Refresh RBAC
          </Button>
        }
      />

      {/* Users Administration Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-sm">
                <Users className="h-4 w-4 text-primary" />
                Operator Accounts Directory
              </CardTitle>
              <CardDescription>
                Role assignment and account lifecycle management with
                privilege-escalation safeguards.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search name or email..."
                  className="h-8 pl-8 text-xs"
                  aria-label="Search users"
                />
              </div>
              <select
                aria-label="Filter users by role"
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="h-8 rounded-md border border-border bg-secondary/40 px-2.5 text-xs text-foreground"
              >
                <option value="">All Roles</option>
                {(rolesQuery.data ?? []).map((r) => (
                  <option key={r.name} value={r.name}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {usersQuery.isLoading ? (
            <LoadingSkeleton cards={2} rows={4} />
          ) : usersQuery.isError ? (
            <ErrorState
              title="Unable to load operator accounts"
              message={normalizeApiError(usersQuery.error).message}
              onRetry={() => usersQuery.refetch()}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-muted-foreground">
                    <th className="px-4 py-2.5 font-medium">Operator</th>
                    <th className="px-4 py-2.5 font-medium">Assigned Role</th>
                    <th className="px-4 py-2.5 font-medium">Permissions</th>
                    <th className="px-4 py-2.5 font-medium">Status</th>
                    <th className="px-4 py-2.5 font-medium">Last Login</th>
                    <th className="px-4 py-2.5 text-right font-medium">
                      Controls
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {(usersQuery.data?.items ?? []).map((u) => (
                    <tr key={u.id} className="hover:bg-muted/20">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-foreground">
                          {u.full_name}
                        </div>
                        <div className="font-mono text-[11px] text-muted-foreground">
                          {u.email}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <PermissionGate
                          permissions={['users:manage', 'roles:manage']}
                          fallback={
                            <Badge variant="default">{u.primary_role}</Badge>
                          }
                        >
                          <select
                            aria-label={`Assign role for ${u.email}`}
                            value={u.primary_role}
                            onChange={(e) =>
                              assignRoleMutation.mutate({
                                userId: u.id,
                                role: e.target.value,
                              })
                            }
                            className="h-8 rounded border border-border bg-secondary/40 px-2 text-xs font-mono text-foreground"
                          >
                            {(rolesQuery.data ?? []).map((r) => (
                              <option key={r.name} value={r.name}>
                                {r.name}
                              </option>
                            ))}
                          </select>
                        </PermissionGate>
                      </td>
                      <td className="px-4 py-3 font-mono text-muted-foreground">
                        {u.permissions.length} granular scopes
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={u.is_active ? 'success' : 'destructive'}>
                          {u.is_active ? 'Active' : 'Suspended'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {formatDateTime(u.last_login_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <PermissionGate permissions={['users:manage']}>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              toggleStatusMutation.mutate({
                                userId: u.id,
                                is_active: !u.is_active,
                              })
                            }
                          >
                            {u.is_active ? (
                              <>
                                <UserX className="mr-1 h-3.5 w-3.5 text-amber-400" />
                                Deactivate
                              </>
                            ) : (
                              <>
                                <UserCheck className="mr-1 h-3.5 w-3.5 text-emerald-400" />
                                Activate
                              </>
                            )}
                          </Button>
                        </PermissionGate>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Roles & Permissions Matrix */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Shield className="h-4 w-4 text-sky-400" />
              Enterprise Governance Roles ({rolesQuery.data?.length ?? 0})
            </CardTitle>
            <CardDescription>
              System and custom roles with assigned permission counts.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {(rolesQuery.data ?? []).map((role) => (
              <div
                key={role.id}
                className="rounded-lg border border-border bg-secondary/40 p-3 text-xs space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-foreground">
                      {role.name}
                    </span>
                    {role.is_system && <Badge variant="info">System</Badge>}
                  </div>
                  <Badge variant="outline">
                    {role.user_count} user(s) • {role.permissions.length} perms
                  </Badge>
                </div>
                <p className="text-muted-foreground">{role.description}</p>
                <div className="flex flex-wrap gap-1">
                  {role.permissions.map((p) => (
                    <span
                      key={p}
                      className="rounded border border-border/60 bg-background px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                    >
                      {p}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <KeyRound className="h-4 w-4 text-primary" />
              Granular Permission Scopes ({permissionsQuery.data?.length ?? 0})
            </CardTitle>
            <CardDescription>
              Database-enforced permission codes across all ParallaxAI modules.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {(permissionsQuery.data ?? []).map((perm) => (
              <div
                key={perm.id}
                className="flex items-center justify-between rounded border border-border bg-secondary/30 px-3 py-2 text-xs"
              >
                <div>
                  <div className="font-mono font-semibold text-foreground">
                    {perm.name}
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    {perm.description}
                  </div>
                </div>
                <Badge variant="outline">{perm.module}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

