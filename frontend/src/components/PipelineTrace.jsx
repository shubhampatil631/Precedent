import React, { useState } from 'react';
import { Tag, Database, MessageSquare, ShieldCheck, Clock, Copy, Check, Twitter, CheckCircle2, ChevronRight, Sparkles, Send } from 'lucide-react';
import DecisionBadge from './DecisionBadge';
import RetrievedEvidence from './RetrievedEvidence';

export default function PipelineTrace({ result }) {
  const [copied, setCopied] = useState(false);

  if (!result) return null;

  const { intent, confidence, retrieved, draft_reply, decision, reason, system_name, latency_ms } = result;

  const confidencePct = (confidence * 100).toFixed(1);
  const isHighConfidence = confidence >= 0.55;

  const handleCopy = () => {
    if (draft_reply) {
      navigator.clipboard.writeText(draft_reply);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const charCount = draft_reply ? draft_reply.length : 0;
  const isWithinTwitterLimit = charCount <= 280;

  return (
    <div className="animate-fade-in" style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '1rem',
      background: '#ffffff',
      borderRadius: '10px',
      border: '1px solid var(--border-default)',
      boxShadow: 'var(--shadow-card)',
      padding: '1.25rem'
    }}>
      {/* Top Meta Bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingBottom: '0.75rem',
        borderBottom: '1px solid var(--border-light)',
        flexWrap: 'wrap',
        gap: '0.4rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)' }}>
            Execution Trace
          </span>
          <span style={{
            fontSize: '0.7rem',
            padding: '2px 7px',
            borderRadius: '4px',
            background: 'var(--brand-subtle)',
            color: 'var(--brand-primary)',
            fontWeight: 700,
            fontFamily: 'var(--font-mono)'
          }}>
            {system_name === 'full' ? 'LangGraph Agent' : system_name === 'simple' ? 'TF-IDF Baseline' : 'Keyword Baseline'}
          </span>
        </div>

        {latency_ms !== undefined && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.3rem',
            fontSize: '0.72rem',
            color: 'var(--text-secondary)',
            fontFamily: 'var(--font-mono)'
          }}>
            <Clock size={12} color="var(--text-muted)" />
            <span>{latency_ms} ms</span>
          </div>
        )}
      </div>

      {/* Decision Status Banner */}
      <DecisionBadge decision={decision} reason={reason} rule_fired={result.rule_fired} />

      {/* Connected 3-Step Execution Timeline (Fluid, Seamless) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginTop: '0.5rem', paddingLeft: '0.25rem' }}>

        {/* Step 1: Intent Classification */}
        <div className="timeline-item">
          <div className="timeline-node">1</div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Intent Classification
              </span>
              <span style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                color: isHighConfidence ? 'var(--status-success-text)' : 'var(--status-warning-text)'
              }}>
                {confidencePct}% confidence
              </span>
            </div>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'var(--bg-surface-subtle)',
              padding: '0.5rem 0.75rem',
              borderRadius: '6px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Tag size={13} color="var(--brand-primary)" />
                <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--brand-primary)', fontFamily: 'var(--font-mono)' }}>
                  {intent}
                </span>
              </div>

              {/* Minimalist Bar */}
              <div style={{ width: '80px', height: '4px', background: '#e2e8f0', borderRadius: '2px', overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${Math.min(100, Math.max(0, confidence * 100))}%`,
                    height: '100%',
                    background: isHighConfidence ? 'var(--status-success)' : 'var(--status-warning)'
                  }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Step 2: Grounded Precedents */}
        <div className="timeline-item">
          <div className="timeline-node">2</div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                ChromaDB Precedent Grounding
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                {retrieved?.length || 0} retrieved (≥ 0.35)
              </span>
            </div>

            <RetrievedEvidence retrieved={retrieved} />
          </div>
        </div>

        {/* Step 3: Grounded Reply Draft */}
        <div className="timeline-item">
          <div className="timeline-node">3</div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Brand Reply Output
              </span>
              {draft_reply && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{ fontSize: '0.7rem', color: isWithinTwitterLimit ? 'var(--text-muted)' : 'var(--status-danger)', fontFamily: 'var(--font-mono)' }}>
                    {charCount}/280
                  </span>
                  <button
                    type="button"
                    onClick={handleCopy}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.2rem',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: 'var(--bg-surface-subtle)',
                      fontSize: '0.7rem',
                      color: 'var(--text-secondary)',
                      fontWeight: 600
                    }}
                  >
                    {copied ? <Check size={10} color="var(--status-success)" /> : <Copy size={10} />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              )}
            </div>

            {/* Seamless Output Bubble */}
            <div style={{
              background: 'var(--bg-app)',
              borderRadius: '8px',
              padding: '0.75rem',
              border: '1px solid var(--border-default)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.35rem' }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  @AmericanAir
                </span>
                <CheckCircle2 size={12} fill="#1d9bf0" color="#ffffff" />
              </div>
              <p style={{
                fontSize: '0.825rem',
                lineHeight: 1.45,
                color: draft_reply ? 'var(--text-primary)' : 'var(--text-muted)',
                fontStyle: draft_reply ? 'normal' : 'italic'
              }}>
                {draft_reply || 'Message escalated directly for human specialist handling.'}
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
