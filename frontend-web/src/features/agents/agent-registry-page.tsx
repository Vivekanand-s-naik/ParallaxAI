import * as React from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowUpRight,
  Bot,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Sliders,
  UserCheck,
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { EmptyState } from '@/components/feedback/empty-state';
import { ErrorState } from '@/components/feedback/error-state';
import { LoadingSkeleton } from '@/components/feedback/loading-skeleton';
import { useUiStore } from '@/stores/ui-store';
import { normalizeApiError } from '@/services/api-error';
import { formatPercent } from '@/lib/utils';

export function AgentRegistryPage() {
  const queryClient = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);

  const [search, setSearch] = React.useState('');
  const [typeFilter, setTypeFilter] = React.useState('');
  const [registerOpen, setRegisterOpen] = React.useState(false);

  // Registration form state
  const [name, setName] = React.useState('');
  const [agentType, setAgentType] = React.useState<'ai' | 'human'>('ai');
  const [provider, setProvider] = React.useState('openai');
  const [modelVersion, setModelVersion] = React.useState('gpt-4o');
  const [role, setRole] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [influenceWeight, setInfluenceWeight] = React.useState(1.0);
  const [confidenceThreshold, setConfidenceThreshold] = React.useState(0.75);

  const filters = React.useMemo(
    () => ({
      type: typeFilter || undefined,
      search: search.trim() || undefined,
    }),
    [typeFilter, search]
  );

  const agentsQuery = useQuery({
    queryKey: queryKeys.agents.list(filters),
    queryFn: () => platformServices.listAgents(filters),
  });

  const registerMutation = useMutation({
    mutationFn: (
      payload: Parameters<typeof platformServices.registerAgent>[0]
    ) => platformServices.registerAgent(payload),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.system.stats() });
      setRegisterOpen(false);
      setName('');
      setRole('');
      setDescription('');
      addToast({
        title: 'Governance Agent Registered',
        description: `${created.name} (${created.code}) added to active evaluation roster.`,
        variant: 'success',
      });
    },
    onError: (err) => {
      addToast({
        title: 'Failed to register agent',
        description: normalizeApiError(err).message,
        variant: 'error',
      });
    },
  });

  const updateAgentMutation = useMutation({
    mutationFn: ({
      agentId,
      payload,
    }: {
      agentId: string;
      payload: Parameters<typeof platformServices.updateAgent>[1];
    }) => platformServices.updateAgent(agentId, payload),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.agents.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.system.stats() });
      addToast({
        title: 'Agent Updated',
        description: `${updated.name} status/weight updated.`,
        variant: 'info',
      });
    },
    onError: (err) => {
      addToast({
        title: 'Failed to update agent',
        description: normalizeApiError(err).message,
        variant: 'error',
      });
    },
  });

  const handleRegisterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim().length < 2 || role.trim().length < 2) {
      addToast({
        title: 'Validation error',
        description: 'Agent name and governance role are required.',
        variant: 'warning',
      });
      return;
    }
    registerMutation.mutate({
      name: name.trim(),
      type: agentType,
      provider: agentType === 'human' ? 'human' : provider,
      model_version: agentType === 'human' ? 'human-expert' : modelVersion,
      role: role.trim(),
      description: description.trim() || undefined,
      influence_weight: influenceWeight,
      confidence_threshold: confidenceThreshold,
      is_active: true,
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI & Human Agent Registry"
        description="Configure multi-provider AI evaluators and human domain reviewers, calibrate influence weights, and audit voting reliability."
        badge={
          <Badge variant="default">
            {agentsQuery.data?.length ?? 0} Registered Agents
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => agentsQuery.refetch()}
              disabled={agentsQuery.isFetching}
            >
              <RefreshCw
                className={`mr-1.5 h-3.5 w-3.5 ${
                  agentsQuery.isFetching ? 'animate-spin' : ''
                }`}
              />
              Refresh
            </Button>
            <PermissionGate permissions={['agents:manage']}>
              <Button size="sm" onClick={() => setRegisterOpen(true)}>
                <Plus className="mr-1.5 h-4 w-4" />
                Register Agent
              </Button>
            </PermissionGate>
          </div>
        }
      />

      {/* Filter Bar */}
      <Card>
        <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search agents by name or governance role..."
              className="pl-9"
              aria-label="Search agents"
            />
          </div>
          <select
            aria-label="Filter by agent type"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="h-9 rounded-md border border-border bg-secondary/40 px-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">All Agent Types</option>
            <option value="ai">AI Evaluators</option>
            <option value="human">Human Reviewers</option>
          </select>
        </CardContent>
      </Card>

      {agentsQuery.isLoading ? (
        <LoadingSkeleton cards={6} rows={2} />
      ) : agentsQuery.isError ? (
        <ErrorState
          title="Unable to load agent registry"
          message={normalizeApiError(agentsQuery.error).message}
          onRetry={() => agentsQuery.refetch()}
        />
      ) : !agentsQuery.data || agentsQuery.data.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="No governance agents found"
          description="Register an AI evaluator or human domain reviewer to begin collaborative governance."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {agentsQuery.data.map((agent) => {
            const isAi = agent.type === 'ai';
            return (
              <Card key={agent.id} className="flex flex-col justify-between">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div
                        className={`flex h-10 w-10 items-center justify-center rounded-lg border ${
                          isAi
                            ? 'border-primary/40 bg-primary/15 text-primary'
                            : 'border-sky-500/40 bg-sky-500/15 text-sky-300'
                        }`}
                      >
                        {isAi ? (
                          <Bot className="h-5 w-5" />
                        ) : (
                          <UserCheck className="h-5 w-5" />
                        )}
                      </div>
                      <div>
                        <CardTitle className="text-sm font-semibold">
                          {agent.name}
                        </CardTitle>
                        <CardDescription className="text-xs">
                          {agent.role}
                        </CardDescription>
                      </div>
                    </div>
                    <Badge variant={agent.is_active ? 'success' : 'outline'}>
                      {agent.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  {agent.description && (
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {agent.description}
                    </p>
                  )}

                  <div className="grid grid-cols-3 gap-2 rounded-lg border border-border bg-secondary/40 p-2.5 text-center text-xs">
                    <div>
                      <div className="text-[10px] text-muted-foreground">
                        Influence
                      </div>
                      <div className="font-mono font-semibold text-foreground">
                        {agent.influence_weight.toFixed(2)}x
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-muted-foreground">
                        Avg Conf
                      </div>
                      <div className="font-mono font-semibold text-sky-400">
                        {formatPercent(agent.average_confidence * 100)}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-muted-foreground">
                        Votes Cast
                      </div>
                      <div className="font-mono font-semibold text-foreground">
                        {agent.vote_count}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {agent.provider ?? agent.type} •{' '}
                      {agent.model_version ?? agent.code}
                    </span>

                    <div className="flex items-center gap-1.5">
                      <PermissionGate permissions={['agents:manage']}>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            updateAgentMutation.mutate({
                              agentId: agent.id,
                              payload: { is_active: !agent.is_active },
                            })
                          }
                        >
                          <Sliders className="mr-1 h-3.5 w-3.5" />
                          {agent.is_active ? 'Pause' : 'Activate'}
                        </Button>
                      </PermissionGate>
                      <Button asChild variant="secondary" size="sm">
                        <Link to={`/app/agents/${agent.id}`}>
                          Profile
                          <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
                        </Link>
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Register Agent Modal */}
      <Dialog open={registerOpen} onOpenChange={setRegisterOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Register Governance Participant Agent</DialogTitle>
            <DialogDescription>
              Add an AI model evaluator or human domain reviewer to the
              ParallaxAI governance roster.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleRegisterSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="agent-name">Agent Display Name</Label>
              <Input
                id="agent-name"
                placeholder="e.g., Claude 3.5 Fairness Auditor"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="agent-type">Participant Type</Label>
                <select
                  id="agent-type"
                  value={agentType}
                  onChange={(e) =>
                    setAgentType(e.target.value as 'ai' | 'human')
                  }
                  className="h-9 w-full rounded-md border border-border bg-secondary/40 px-3 text-xs text-foreground"
                >
                  <option value="ai">AI Evaluator</option>
                  <option value="human">Human Reviewer</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="agent-provider">Provider</Label>
                <Input
                  id="agent-provider"
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  disabled={agentType === 'human'}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="agent-role">Governance Role</Label>
                <Input
                  id="agent-role"
                  placeholder="e.g., Compliance & Bias Specialist"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="agent-model">Model / Credential Version</Label>
                <Input
                  id="agent-model"
                  value={modelVersion}
                  onChange={(e) => setModelVersion(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="agent-weight">
                  Influence Weight ({influenceWeight.toFixed(2)}x)
                </Label>
                <Input
                  id="agent-weight"
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="5.0"
                  value={influenceWeight}
                  onChange={(e) => setInfluenceWeight(Number(e.target.value))}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="agent-threshold">
                  Confidence Threshold ({Math.round(confidenceThreshold * 100)}%)
                </Label>
                <Input
                  id="agent-threshold"
                  type="number"
                  step="0.05"
                  min="0.1"
                  max="1.0"
                  value={confidenceThreshold}
                  onChange={(e) =>
                    setConfidenceThreshold(Number(e.target.value))
                  }
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="agent-desc">Description</Label>
              <Textarea
                id="agent-desc"
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="ghost"
                onClick={() => setRegisterOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={registerMutation.isPending}>
                {registerMutation.isPending && (
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                )}
                Register Agent
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

