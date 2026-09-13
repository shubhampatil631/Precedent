import React, { useEffect, useState } from 'react';
import { RefreshCw, BarChart2, AlertCircle } from 'lucide-react';
import EvalDashboard from '../components/EvalDashboard';
import { getEvalResults } from '../api';

export default function EvalResults() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getEvalResults();
      setResults(data);
    } catch (err) {
      setError(err.message || 'Failed to load evaluation results.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}>
      {/* Top Header */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-default)',
        borderRadius: '12px',
        padding: '0.85rem 1.25rem',
        boxShadow: 'var(--shadow-xs)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'var(--brand-subtle)',
            color: 'var(--brand-primary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            <BarChart2 size={18} />
          </div>
          <div>
            <h2 style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.2 }}>
              Evaluation Benchmarks & Insights
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.74rem', lineHeight: 1.2, marginTop: '2px' }}>
              Systematic evaluation comparing Trivial, Simple, and Full LangGraph Pipeline across 160 golden test samples.
            </p>
          </div>
        </div>

        <button
          onClick={fetchResults}
          disabled={loading}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
            padding: '0.45rem 0.9rem',
            borderRadius: '6px',
            background: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-default)',
            color: 'var(--text-primary)',
            fontSize: '0.75rem',
            fontWeight: 600,
            transition: 'all 0.15s ease'
          }}
        >
          <RefreshCw size={12} className={loading ? 'pulse-dot' : ''} />
          <span>{loading ? 'Refreshing...' : 'Refresh Benchmark Data'}</span>
        </button>
      </div>

      {error && (
        <div style={{
          background: 'var(--status-danger-bg)',
          border: '1px solid var(--status-danger-border)',
          borderRadius: '10px',
          padding: '0.75rem 1rem',
          color: 'var(--status-danger-text)',
          fontSize: '0.8rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <EvalDashboard results={results} />
    </div>
  );
}
