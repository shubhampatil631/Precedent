import React, { useState } from 'react';
import { Database, MessageSquare, CheckCircle, ChevronDown, ChevronUp, Sparkles, ExternalLink } from 'lucide-react';

export default function RetrievedEvidence({ retrieved }) {
  const [expandedId, setExpandedId] = useState(null);

  if (!retrieved || retrieved.length === 0) {
    return (
      <div style={{
        padding: '0.85rem',
        background: 'var(--bg-surface-subtle)',
        borderRadius: '6px',
        color: 'var(--text-secondary)',
        fontSize: '0.78rem',
        textAlign: 'center',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.4rem'
      }}>
        <Database size={15} style={{ color: 'var(--text-muted)' }} />
        <span>No precedents retrieved above calibrated threshold floor (≥ 0.35).</span>
      </div>
    );
  }

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
      {retrieved.map((item, idx) => {
        const simPct = (item.similarity * 100).toFixed(1);
        const isHighSim = item.similarity >= 0.55;
        const threadKey = item.thread_id || idx;
        const isExpanded = expandedId === threadKey || (expandedId === null && idx === 0);

        return (
          <div
            key={threadKey}
            style={{
              background: 'var(--bg-surface-subtle)',
              borderRadius: '6px',
              overflow: 'hidden',
              transition: 'background 0.15s ease'
            }}
          >
            {/* Header Row */}
            <div
              onClick={() => toggleExpand(threadKey)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.45rem 0.65rem',
                cursor: 'pointer',
                userSelect: 'none'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span style={{
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-mono)'
                }}>
                  Precedent #{idx + 1} {item.thread_id ? `(#${item.thread_id})` : ''}
                </span>
                {idx === 0 && (
                  <span style={{
                    fontSize: '0.6rem',
                    padding: '1px 4px',
                    borderRadius: '3px',
                    background: 'var(--brand-primary)',
                    color: '#ffffff',
                    fontWeight: 700,
                    textTransform: 'uppercase'
                  }}>
                    Top
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-mono)',
                  color: isHighSim ? 'var(--brand-primary)' : 'var(--text-secondary)'
                }}>
                  {simPct}% Sim
                </span>
                {isExpanded ? <ChevronUp size={13} color="var(--text-muted)" /> : <ChevronDown size={13} color="var(--text-muted)" />}
              </div>
            </div>

            {/* Seamless Content */}
            {isExpanded && (
              <div style={{
                padding: '0.5rem 0.65rem 0.65rem 0.65rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.4rem',
                borderTop: '1px solid rgba(0,0,0,0.05)'
              }}>
                {/* Historical Query */}
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
                  <span style={{ color: 'var(--text-muted)', fontWeight: 600, marginRight: '4px' }}>Query:</span>
                  "{item.customer_text}"
                </div>

                {/* Verified Official Resolution */}
                <div style={{
                  padding: '0.4rem 0.55rem',
                  background: '#ffffff',
                  borderRadius: '4px',
                  borderLeft: '2px solid var(--status-success)',
                  fontSize: '0.78rem',
                  color: '#064e3b',
                  lineHeight: 1.35
                }}>
                  <div style={{ fontSize: '0.62rem', fontWeight: 700, color: 'var(--status-success-text)', textTransform: 'uppercase', marginBottom: '2px', letterSpacing: '0.03em' }}>
                    Verified @AmericanAir Precedent
                  </div>
                  "{item.brand_text}"
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
