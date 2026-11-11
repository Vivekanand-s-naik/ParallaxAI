import * as React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle2,
  FileCode2,
  Loader2,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  XCircle,
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
import { ErrorState } from '@/components/feedback/error-state';
import { LoadingSkeleton } from '@/components/feedback/loading-skeleton';
import { useUiStore } from '@/stores/ui-store';
import { normalizeApiError } from '@/services/api-error';
import { formatPercent } from '@/lib/utils';

export function GovernanceConsolePage() {
  const queryClient = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);

  const [createOpen, setCreateOpen] = React.useState(false);
  const [name, setName] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [context, setContext] = React.useState('loan_approval');
  const [threshold, setThreshold] = React.useState(0.75);
  const [priority, setPriority] = React.useState(1);
  const [yamlText, setYamlText] = React.useState(
    'max_bias_score: 0.45\nmin_consensus_score: 0.75\nmandatory_human_review: true'
  );
  const [yamlValidation, setYamlValidation] = React.useState<{
    valid?: boolean;
    message?: string;
  }>({});

  const rulesQuery = useQuery({
    queryKey: queryKeys.governance.rules(),
    queryFn: () => platformServices.listGovernanceRules(),
  });

  const validateYamlMutation = useMutation({
    mutationFn: (yaml: string) =>
      platformServices.validateGovernanceYaml(yaml),
    onSuccess: (res) => {
      if (res.valid) {
        setYamlValidation({
          valid: true,
          message: `Valid YAML policy (${(res.keys ?? []).join(', ')})`,
        });
      } else {
        setYamlValidation({
          valid: false,
          message: res.error ?? 'Invalid YAML policy definition.',
        });
      }
    },
  });

  const createRuleMutation = useMutation({
    mutationFn: (
      payload: Parameters<typeof platformServices.createGovernanceRule>[0]
    ) => platformServices.createGovernanceRule(payload),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.governance.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.system.stats() });
      setCreateOpen(false);
      setName('');
      setDescription('');
      addToast({
        title: 'Governance Policy Created',
        description: `Rule "${created.name}" is now active across ${created.context}.`,
        variant: 'success',
      });
    },
    onError: (err) => {
      addToast({
        title: 'Failed to create policy',
        description: normalizeApiError(err).message,
        variant: 'error',
      });
    },
  });

  const toggleRuleMutation = useMutation({
    mutationFn: ({
      ruleId,
      is_active,
    }: {
      ruleId: string;
      is_active: boolean;
    }) => platformServices.updateGovernanceRule(ruleId, { is_active }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.governance.all });
      addToast({
        title: 'Policy Status Updated',
        description: `${updated.name} is now ${
          updated.is_active ? 'active' : 'paused'
        }.`,
        variant: 'info',
      });
    },
  });

  const deleteRuleMutation = useMutation({
    mutationFn: (ruleId: string) =>
      platformServices.deleteGovernanceRule(ruleId),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.governance.all });
      addToast({
        title: 'Governance Policy Deleted',
        description: res.message,
        variant: 'info',
      });
    },
  });

  const handleCreateRule = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !description.trim()) {
      addToast({
        title: 'Validation error',
        description: 'Policy name and description are required.',
        variant: 'warning',
      });
      return;
    }
    createRuleMutation.mutate({
      name: name.trim(),
      description: description.trim(),
      context,
      policy_type: 'threshold',
      rule_definition: yamlText,
      approval_threshold: threshold,
      require_human_review: true,
      is_active: true,
      priority,
    });
  };

  return (
    <div className="space-y-6" data-testid="governance-console-page">
      <PageHeader
        title="Governance Policy Console & Rule Engine"
        description="Author, validate, and enforce declarative YAML governance policies, consensus approval thresholds, and human-in-the-loop escalation triggers."
        badge={
          <Badge variant="default">
            {rulesQuery.data?.length ?? 0} Policy Rules
          </Badge>
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => rulesQuery.refetch()}
            >
              <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
              Refresh
            </Button>
            <PermissionGate permissions={['governance:manage']}>
              <Button size="sm" onClick={() => setCreateOpen(true)}>
                <Plus className="mr-1.5 h-4 w-4" />
                Author Policy Rule
              </Button>
            </PermissionGate>
          </div>
        }
      />

      {rulesQuery.isLoading ? (
        <LoadingSkeleton cards={3} rows={3} />
      ) : rulesQuery.isError ? (
        <ErrorState
          title="Unable to load governance policies"
          message={normalizeApiError(rulesQuery.error).message}
          onRetry={() => rulesQuery.refetch()}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {(rulesQuery.data ?? []).map((rule) => (
            <Card key={rule.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <CardTitle className="flex items-center gap-2 text-sm">
                      <FileCode2 className="h-4 w-4 text-primary" />
                      {rule.name}
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {rule.description}
                    </CardDescription>
                  </div>
                  <Badge variant={rule.is_active ? 'success' : 'outline'}>
                    {rule.is_active ? 'Enforced' : 'Paused'}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <Badge variant="info">
                    Context: {rule.context.replace(/_/g, ' ')}
                  </Badge>
                  <Badge variant="default">
                    Approval Threshold:{' '}
                    {formatPercent(rule.approval_threshold * 100)}
                  </Badge>
                  <Badge variant="outline">Priority #{rule.priority}</Badge>
                </div>

                <pre className="max-h-36 overflow-x-auto rounded-lg border border-border bg-background p-3 font-mono text-xs text-muted-foreground">
                  {rule.rule_definition}
                </pre>

                <PermissionGate permissions={['governance:manage']}>
                  <div className="flex items-center justify-end gap-2 pt-1">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() =>
                        toggleRuleMutation.mutate({
                          ruleId: rule.id,
                          is_active: !rule.is_active,
                        })
                      }
                    >
                      {rule.is_active ? 'Pause Policy' : 'Enable Policy'}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteRuleMutation.mutate(rule.id)}
                      className="text-red-400 hover:bg-red-500/10"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </PermissionGate>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Policy Modal */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Author Declarative Governance Policy</DialogTitle>
            <DialogDescription>
              Define YAML policy constraints and consensus thresholds for automated
              and human-in-the-loop enforcement.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateRule} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="policy-name">Policy Name</Label>
              <Input
                id="policy-name"
                placeholder="e.g., Clinical Diagnostic High-Risk Escalation"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="policy-desc">Policy Description</Label>
              <Input
                id="policy-desc"
                placeholder="Describe regulatory or ethical mandate..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="policy-context">Domain Context</Label>
                <select
                  id="policy-context"
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  className="h-9 w-full rounded-md border border-border bg-secondary/40 px-2.5 text-xs text-foreground"
                >
                  <option value="loan_approval">Loan Approval</option>
                  <option value="medical_diagnosis">Medical Diagnosis</option>
                  <option value="hiring_assessment">Hiring Assessment</option>
                  <option value="content_moderation">Content Moderation</option>
                  <option value="financial_trading">Financial Trading</option>
                  <option value="general">General</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="policy-threshold">
                  Threshold ({Math.round(threshold * 100)}%)
                </Label>
                <Input
                  id="policy-threshold"
                  type="number"
                  step="0.05"
                  min="0.5"
                  max="1.0"
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="policy-priority">Priority</Label>
                <Input
                  id="policy-priority"
                  type="number"
                  min="1"
                  max="10"
                  value={priority}
                  onChange={(e) => setPriority(Number(e.target.value))}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="policy-yaml">YAML Policy Definition</Label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => validateYamlMutation.mutate(yamlText)}
                >
                  <ShieldCheck className="mr-1 h-3.5 w-3.5 text-sky-400" />
                  Validate YAML
                </Button>
              </div>
              <Textarea
                id="policy-yaml"
                rows={4}
                className="font-mono text-xs"
                value={yamlText}
                onChange={(e) => setYamlText(e.target.value)}
              />
              {yamlValidation.message && (
                <p
                  className={`flex items-center gap-1 text-xs ${
                    yamlValidation.valid ? 'text-emerald-400' : 'text-red-400'
                  }`}
                >
                  {yamlValidation.valid ? (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5" />
                  )}
                  {yamlValidation.message}
                </p>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="ghost"
                onClick={() => setCreateOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createRuleMutation.isPending}>
                {createRuleMutation.isPending && (
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                )}
                Deploy Governance Rule
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

