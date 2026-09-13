import React, { useState } from 'react';
import { Bot, BarChart3, Layers, ShieldCheck, Database, Plane, CheckCircle2, Terminal } from 'lucide-react';
import TryAgent from './pages/TryAgent';
import EvalResults from './pages/EvalResults';
import TaxonomyExplorer from './components/TaxonomyExplorer';

export default function App() {
  const [activeTab, setActiveTab] = useState('try-agent');

  return (
    <div style={{ minHeight: '100vh', width: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-app)' }}>
      {/* Top Enterprise SaaS Navigation Header */}
      <header style={{
        background: '#ffffff',
        borderBottom: '1px solid var(--border-default)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        boxShadow: 'var(--shadow-xs)',
        width: '100%'
      }}>
        <div style={{
          maxWidth: '1380px',
          margin: '0 auto',
          padding: '0.6rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          flexWrap: 'wrap'
        }}>
          {/* Brand & Partner Badges */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #1d4ed8, #2563eb)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              boxShadow: '0 2px 5px rgba(37, 99, 235, 0.25)',
              flexShrink: 0
            }}>
              <Plane size={17} strokeWidth={2.2} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <h1 style={{ fontSize: '0.975rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-primary)', lineHeight: 1.2 }}>
                  Precedent AI
                </h1>
                <span style={{
                  fontSize: '0.62rem',
                  fontWeight: 700,
                  padding: '1px 5px',
                  borderRadius: '4px',
                  background: 'var(--brand-subtle)',
                  color: 'var(--brand-primary)',
                  border: '1px solid var(--brand-border)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.02em'
                }}>
                  v1.0 Pro
                </span>
              </div>
              <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.2 }}>
                Support Agent for <strong style={{ color: 'var(--text-secondary)' }}>@AmericanAir</strong>
              </p>
            </div>
          </div>

          {/* Center Navigation Tabs */}
          <nav style={{
            display: 'flex',
            gap: '0.25rem',
            background: 'var(--bg-surface-subtle)',
            padding: '3px',
            borderRadius: '8px',
            border: '1px solid var(--border-default)'
          }}>
            {[
              { id: 'try-agent', label: 'Agent Console', icon: Bot },
              { id: 'eval-results', label: 'Benchmark Hub', icon: BarChart3 },
              { id: 'taxonomy', label: '12-Intent Taxonomy', icon: Layers }
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    padding: '5px 12px',
                    borderRadius: '6px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    background: isActive ? '#ffffff' : 'transparent',
                    color: isActive ? 'var(--brand-primary)' : 'var(--text-secondary)',
                    boxShadow: isActive ? 'var(--shadow-xs)' : 'none',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <Icon size={14} color={isActive ? 'var(--brand-primary)' : 'var(--text-muted)'} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>

          {/* System Status Indicators */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              padding: '3px 8px',
              borderRadius: '8px',
              background: 'var(--status-success-bg)',
              border: '1px solid var(--status-success-border)',
              fontSize: '0.7rem',
              fontWeight: 700,
              color: 'var(--status-success-text)'
            }}>
              <span style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: 'var(--status-success)',
                display: 'inline-block'
              }} className="pulse-dot" />
              <span>FastAPI :8000</span>
            </div>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem',
              padding: '3px 8px',
              borderRadius: '8px',
              background: 'var(--bg-surface-subtle)',
              border: '1px solid var(--border-default)',
              fontSize: '0.7rem',
              fontWeight: 600,
              color: 'var(--text-secondary)'
            }}>
              <Database size={12} color="var(--text-muted)" />
              <span>2,000 Precedents</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main SaaS Workspace Container (Clean Medium-Density Grid) */}
      <main style={{
        flex: 1,
        maxWidth: '1380px',
        width: '100%',
        margin: '0 auto',
        padding: '1.25rem',
        boxSizing: 'border-box'
      }}>
        {activeTab === 'try-agent' && <TryAgent />}
        {activeTab === 'eval-results' && <EvalResults />}
        {activeTab === 'taxonomy' && <TaxonomyExplorer />}
      </main>

      {/* Clean Enterprise Footer */}
      <footer style={{
        borderTop: '1px solid var(--border-default)',
        background: '#ffffff',
        width: '100%'
      }}>
        <div style={{
          maxWidth: '1380px',
          margin: '0 auto',
          padding: '0.75rem 1.25rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
          fontSize: '0.72rem',
          color: 'var(--text-muted)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <ShieldCheck size={13} color="var(--status-success)" />
            <span>Deterministic Safety Routing & Precedent Grounding Architecture</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span>LangGraph 4-Node Pipeline</span>
            <span>•</span>
            <span>ChromaDB Vector Store</span>
            <span>•</span>
            <span>FastAPI Backend</span>
            <span>•</span>
            <span>React SaaS</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
