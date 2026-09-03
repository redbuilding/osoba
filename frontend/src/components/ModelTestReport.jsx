import React from 'react';
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  FlaskConical,
  Loader2,
} from 'lucide-react';

const STATUS_META = {
  ok: { Icon: CheckCircle2, color: 'text-brand-success-green', label: 'OK' },
  error: { Icon: XCircle, color: 'text-brand-alert-red', label: 'Error' },
  timeout: { Icon: Clock, color: 'text-brand-alert-red', label: 'Timeout' },
  empty: { Icon: AlertTriangle, color: 'text-brand-accent', label: 'Empty' },
};

const ModelTestReport = ({ results = [], summary = {}, loading = false }) => {
  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-brand-text-secondary">
        <Loader2 className="w-4 h-4 animate-spin text-brand-purple" />
        Testing models…
      </div>
    );
  }

  if (!results.length) {
    return (
      <div className="text-sm text-brand-text-secondary">
        No models to test. Configure a provider API key first, then run again.
      </div>
    );
  }

  const total = summary.total ?? results.length;
  const ok = summary.ok ?? results.filter((r) => r.status === 'ok').length;
  const failed = total - ok;

  return (
    <div className="w-full">
      <div className="flex items-center gap-2 mb-2">
        <FlaskConical size={18} className="text-brand-purple flex-shrink-0" />
        <span className="font-semibold text-sm text-brand-text-primary">Model Diagnostics</span>
      </div>

      <div className="flex items-center gap-3 text-xs text-brand-text-secondary mb-3">
        <span>{total} models</span>
        <span className="text-brand-success-green">{ok} ok</span>
        {failed > 0 && <span className="text-brand-alert-red">{failed} failed</span>}
        {summary.avg_latency_ms != null && (
          <span>avg {summary.avg_latency_ms} ms</span>
        )}
      </div>

      <div className="space-y-1.5">
        {results.map((r, idx) => {
          const meta = STATUS_META[r.status] || STATUS_META.error;
          const { Icon } = meta;
          const isOk = r.status === 'ok';
          return (
            <div
              key={`${r.model}-${idx}`}
              className="rounded-md border border-gray-700 bg-black/20 p-2"
            >
              <div className="flex items-center gap-2">
                <Icon size={15} className={`${meta.color} flex-shrink-0`} />
                <span className="text-sm font-mono text-brand-text-primary truncate" title={r.model}>
                  {r.model}
                </span>
                <span className="ml-auto text-xs text-brand-text-secondary whitespace-nowrap">
                  {isOk ? `${r.latency_ms} ms` : meta.label}
                </span>
              </div>
              {isOk && r.text && (
                <p className="mt-1 text-xs text-brand-text-secondary italic break-words">{r.text}</p>
              )}
              {!isOk && r.error && (
                <p className="mt-1 text-xs text-brand-alert-red break-words">{r.error}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ModelTestReport;