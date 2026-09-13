import React from 'react';
import { CheckCircle2, ShieldAlert, ShieldCheck } from 'lucide-react';

export default function DecisionBadge({ decision, reason, rule_fired }) {
  const isAutoHandle = decision === 'auto_handle';

  return (
    <div
      className="animate-fade-in"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem',
        padding: '0.65rem 0.9rem',
        borderRadius: '8px',
        background: isAutoHandle ? 'var(--status-success-bg)' : 'var(--status-danger-bg)',
        borderLeft: `3px solid ${isAutoHandle ? 'var(--status-success)' : 'var(--status-danger)'}`
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, minWidth: '240px' }}>
        {isAutoHandle ? (
          <CheckCircle2 size={16} color="var(--status-success)" strokeWidth={2.5} style={{ flexShrink: 0 }} />
        ) : (
          <ShieldAlert size={16} color="var(--status-danger)" strokeWidth={2.5} style={{ flexShrink: 0 }} />
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
            <span style={{
              fontSize: '0.8rem',
              fontWeight: 800,
              color: isAutoHandle ? 'var(--status-success-text)' : 'var(--status-danger-text)'
            }}>
              {isAutoHandle ? 'Auto-Handle Approved' : 'Escalated to Human Specialist'}
            </span>

            {rule_fired && (
              <span style={{
                fontSize: '0.65rem',
                padding: '1px 5px',
                borderRadius: '3px',
                background: '#ffffff',
                color: 'var(--text-secondary)',
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                border: '1px solid var(--border-light)'
              }}>
                {rule_fired}
              </span>
            )}
          </div>

          <div style={{ fontSize: '0.74rem', color: isAutoHandle ? '#065f46' : '#991b1b', lineHeight: 1.3 }}>
            {reason}
          </div>
        </div>
      </div>
    </div>
  );
}
