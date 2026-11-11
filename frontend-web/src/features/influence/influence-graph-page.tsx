import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Network, RefreshCw } from 'lucide-react';
import { queryKeys } from '@/app/query-client';
import { platformServices } from '@/services/platform-services';
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
import { ErrorState } from '@/components/feedback/error-state';
import { LoadingSkeleton } from '@/components/feedback/loading-skeleton';
import { normalizeApiError } from '@/services/api-error';
import { formatPercent } from '@/lib/utils';

export function InfluenceGraphPage() {
  const graphQuery = useQuery({
    queryKey: queryKeys.agents.influenceGraph(),
    queryFn: () => platformServices.getInfluenceGraph(),
  });

  const { flowNodes, flowEdges, agentNodesList, agreementEdgesList } =
    React.useMemo(() => {
      const rawNodes = (graphQuery.data?.nodes ?? []) as unknown as Array<
        Record<string, unknown>
      >;
      const rawEdges = (graphQuery.data?.edges ?? []) as unknown as Array<
        Record<string, unknown>
      >;
      const count = Math.max(rawNodes.length, 1);
      const radius = 190;

      const nodes: Node[] = rawNodes.map((n, index) => {
        const nodeData = (n.data ?? {}) as Record<string, unknown>;
        const pos = n.position as { x: number; y: number } | undefined;
        const angle = (2 * Math.PI * index) / count;
        const x = pos?.x ?? 320 + radius * Math.cos(angle);
        const y = pos?.y ?? 210 + radius * Math.sin(angle);

        const entityType = String(nodeData.entity_type ?? n.type ?? 'agent');
        const agentType = String(nodeData.agent_type ?? n.type ?? 'ai');
        const name = String(nodeData.label ?? n.name ?? n.id);
        const weight = Number(
          nodeData.influence_weight ?? n.influence_weight ?? 1.0
        );
        const isDecision = entityType === 'decision';
        const isAi = agentType === 'ai';

        return {
          id: String(n.id),
          position: { x, y },
          data: {
            label: isDecision ? name : `${name} (${weight.toFixed(2)}x)`,
          },
          style: {
            background: isDecision
              ? '#1e1b4b'
              : isAi
                ? '#111c35'
                : '#0f2937',
            color: '#f8fafc',
            border: isDecision
              ? '1px solid #8b5cf6'
              : isAi
                ? '1px solid #3b82f6'
                : '1px solid #14b8a6',
            borderRadius: '8px',
            padding: '8px 12px',
            fontSize: '11px',
            fontWeight: 600,
            width: 195,
          },
        };
      });

      const edges: Edge[] = rawEdges.map((e) => {
        const edgeData = (e.data ?? {}) as Record<string, unknown>;
        const rate = Number(
          edgeData.agreement_rate ?? e.agreement_rate ?? 0.75
        );
        const shared = Number(
          edgeData.shared_decisions ?? e.shared_decisions ?? 1
        );
        const label = e.label
          ? String(e.label)
          : `${Math.round(rate * 100)}% (${shared})`;

        return {
          id: String(e.id),
          source: String(e.source),
          target: String(e.target),
          label,
          animated: Boolean(e.animated ?? rate >= 0.75),
          style: {
            stroke: rate >= 0.7 ? '#14b8a6' : '#64748b',
            strokeWidth: Math.max(1.5, rate * 3),
          },
        };
      });

      const parsedAgents = rawNodes
        .filter((n) => {
          const d = (n.data ?? {}) as Record<string, unknown>;
          return (d.entity_type ?? 'agent') === 'agent';
        })
        .map((n) => {
          const d = (n.data ?? {}) as Record<string, unknown>;
          return {
            id: String(n.id),
            name: String(d.label ?? n.name ?? n.id),
            role: String(d.role ?? n.role ?? 'Evaluator'),
            influence_weight: Number(
              d.influence_weight ?? n.influence_weight ?? 1.0
            ),
            vote_count: Number(d.vote_count ?? n.vote_count ?? 0),
          };
        });

      const parsedEdges = rawEdges.map((e) => {
        const d = (e.data ?? {}) as Record<string, unknown>;
        return {
          id: String(e.id),
          source: String(e.source),
          target: String(e.target),
          agreement_rate: Number(d.agreement_rate ?? e.agreement_rate ?? 0.8),
          shared_decisions: Number(
            d.shared_decisions ?? e.shared_decisions ?? 1
          ),
        };
      });

      return {
        flowNodes: nodes,
        flowEdges: edges,
        agentNodesList: parsedAgents,
        agreementEdgesList: parsedEdges,
      };
    }, [graphQuery.data]);

  if (graphQuery.isLoading) {
    return <LoadingSkeleton cards={4} rows={4} />;
  }

  if (graphQuery.isError || !graphQuery.data) {
    return (
      <ErrorState
        title="Unable to load Agent Influence Graph"
        message={
          graphQuery.error
            ? normalizeApiError(graphQuery.error).message
            : 'Graph telemetry unavailable.'
        }
        onRetry={() => graphQuery.refetch()}
      />
    );
  }

  const { metrics } = graphQuery.data;

  return (
    <div className="space-y-6" data-testid="influence-graph-page">
      <PageHeader
        title="Agent Influence & Agreement Network"
        description="Interactive React Flow topology visualizing influence multipliers, pairwise voting alignment, and coalition dynamics between AI models and human reviewers."
        badge={
          <Badge variant="default">
            Density: {formatPercent((metrics.network_density ?? 0) * 100)}
          </Badge>
        }
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => graphQuery.refetch()}
          >
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            Recompute Graph
          </Button>
        }
      />

      {/* Top Metrics */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">Active Nodes</div>
            <div className="mt-1 font-mono text-2xl font-bold text-foreground">
              {metrics.active_agents ?? metrics.total_agents} /{' '}
              {metrics.total_agents}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">
              AI vs Human Split
            </div>
            <div className="mt-1 font-mono text-2xl font-bold text-primary">
              {metrics.ai_agents} AI • {metrics.human_agents} Human
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">
              Avg Pairwise Agreement
            </div>
            <div className="mt-1 font-mono text-2xl font-bold text-sky-400">
              {formatPercent((metrics.average_agreement_rate ?? 0.85) * 100)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground">
              Top Influence Node
            </div>
            <div className="mt-1 truncate text-sm font-semibold text-foreground">
              {metrics.highest_influence_agent ?? 'Dr. Sarah Chen'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Interactive React Flow Canvas */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm">
            <Network className="h-4 w-4 text-primary" />
            Interactive Co-Governance Influence Topology
          </CardTitle>
          <CardDescription>
            Blue nodes represent AI evaluators; teal nodes represent human
            reviewers; violet nodes represent active decision cases.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            className="h-[460px] w-full overflow-hidden rounded-lg border border-border bg-background"
            data-testid="react-flow-container"
          >
            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#1e293b" gap={20} />
              <Controls />
              <MiniMap
                nodeColor={(n) =>
                  String(n.style?.border).includes('#3b82f6')
                    ? '#3b82f6'
                    : '#14b8a6'
                }
              />
            </ReactFlow>
          </div>
        </CardContent>
      </Card>

      {/* Pairwise Agreement & Node Weight Table */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">
              Agent Influence Multipliers ({agentNodesList.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {agentNodesList.map((n) => (
                <div
                  key={n.id}
                  className="flex items-center justify-between rounded border border-border bg-secondary/30 px-3 py-2 text-xs"
                >
                  <div>
                    <span className="font-semibold text-foreground">
                      {n.name}
                    </span>
                    <span className="ml-2 text-muted-foreground">
                      ({n.role})
                    </span>
                  </div>
                  <div className="font-mono text-primary">
                    {n.influence_weight.toFixed(2)}x • {n.vote_count} votes
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">
              Pairwise Voting Agreement & Influence Edges (
              {agreementEdgesList.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {agreementEdgesList.slice(0, 10).map((e) => (
                <div
                  key={e.id}
                  className="flex items-center justify-between rounded border border-border bg-secondary/30 px-3 py-2 text-xs"
                >
                  <span className="font-mono text-foreground">
                    {e.source} ↔ {e.target}
                  </span>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={e.agreement_rate >= 0.7 ? 'success' : 'info'}
                    >
                      {formatPercent(e.agreement_rate * 100)} alignment
                    </Badge>
                    <span className="text-muted-foreground">
                      ({e.shared_decisions} shared)
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
