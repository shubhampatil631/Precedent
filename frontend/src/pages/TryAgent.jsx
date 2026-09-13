import React, { useState } from 'react';
import { AlertCircle, Sliders, ShieldCheck, Zap, Bot, ArrowRight, CheckCircle2 } from 'lucide-react';
import MessageInput from '../components/MessageInput';
import PipelineTrace from '../components/PipelineTrace';
import { handleMessage } from '../api';

export default function TryAgent() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [compareResults, setCompareResults] = useState(null);
  const [compareBaselines, setCompareBaselines] = useState(false);
  const [selectedSystem, setSelectedSystem] = useState('full');
  const [error, setError] = useState(null);

  const handleRun = async (text) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setCompareResults(null);

    try {
      if (compareBaselines) {
        const [fullRes, simpleRes, trivialRes] = await Promise.all([
          handleMessage(text, 'full').catch(err => ({ error: err.message, system_name: 'full' })),
          handleMessage(text, 'simple').catch(err => ({ error: err.message, system_name: 'simple' })),
          handleMessage(text, 'trivial').catch(err => ({ error: err.message, system_name: 'trivial' }))
        ]);

        setCompareResults({
          full: fullRes,
          simple: simpleRes,
          trivial: trivialRes
        });
      } else {
        const data = await handleMessage(text, selectedSystem);
        setResult(data);
      }
    } catch (err) {
      setError(err.message || 'An error occurred while executing the support pipeline.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
      {/* Modern Seamless Top Bar (Un-Boxy) */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem',
        paddingBottom: '0.25rem'
      }}>
        <div>
          <h2 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.2 }}>
            Support Agent Workstation
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginTop: '2px' }}>
            LangGraph 4-node pipeline with ChromaDB vector grounding & deterministic safety routing.
          </p>
        </div>

        {/* Guarantees Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.3rem',
            padding: '3px 7px',
            borderRadius: '4px',
            background: 'var(--status-success-bg)',
            fontSize: '0.7rem',
            fontWeight: 700,
            color: 'var(--status-success-text)'
          }}>
            <ShieldCheck size={12} />
            <span>0.0% Safety Violations</span>
          </div>

          <div style={{
            padding: '3px 7px',
            borderRadius: '4px',
            background: 'var(--bg-surface-subtle)',
            fontSize: '0.7rem',
            fontWeight: 600,
            color: 'var(--text-secondary)'
          }}>
            <span>Confidence: <strong>≥ 55%</strong></span>
          </div>

          <div style={{
            padding: '3px 7px',
            borderRadius: '4px',
            background: 'var(--bg-surface-subtle)',
            fontSize: '0.7rem',
            fontWeight: 600,
            color: 'var(--text-secondary)'
          }}>
            <span>Cosine Sim: <strong>≥ 0.35</strong></span>
          </div>
        </div>
      </div>

      {error && (
        <div style={{
          background: 'var(--status-danger-bg)',
          borderRadius: '8px',
          padding: '0.65rem 0.9rem',
          color: 'var(--status-danger-text)',
          fontSize: '0.8rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          borderLeft: '3px solid var(--status-danger)'
        }}>
          <AlertCircle size={15} />
          <div><strong>Execution Error:</strong> {error}</div>
        </div>
      )}

      {/* Main Workstation Layout */}
      {!compareBaselines ? (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(380px, 440px) 1fr',
          gap: '1.5rem',
          alignItems: 'start',
          width: '100%'
        }}>
          {/* Left Column: Input Ticket Stream */}
          <div>
            <MessageInput
              onRun={handleRun}
              loading={loading}
              selectedSystem={selectedSystem}
              setSelectedSystem={setSelectedSystem}
              compareBaselines={compareBaselines}
              setCompareBaselines={setCompareBaselines}
            />
          </div>

          {/* Right Column: Realtime Trace Canvas */}
          <div>
            {result ? (
              <PipelineTrace result={result} />
            ) : (
              <div style={{
                background: '#ffffff',
                borderRadius: '10px',
                border: '1px dashed var(--border-default)',
                padding: '3.5rem 1.5rem',
                textAlign: 'center',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '0.6rem'
              }}>
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  background: 'var(--bg-surface-subtle)',
                  color: 'var(--brand-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Zap size={18} />
                </div>
                <div>
                  <h3 style={{ fontSize: '0.925rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.15rem' }}>
                    Agent Execution Canvas
                  </h3>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', maxWidth: '380px' }}>
                    Select a preset test scenario or enter a customer tweet on the left to run the live pipeline.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* 3-Way Comparative Layout */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
          <MessageInput
            onRun={handleRun}
            loading={loading}
            selectedSystem={selectedSystem}
            setSelectedSystem={setSelectedSystem}
            compareBaselines={compareBaselines}
            setCompareBaselines={setCompareBaselines}
          />

          {compareResults && (
            <div style={{ marginTop: '0.5rem', width: '100%' }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '0.75rem',
                paddingBottom: '0.4rem',
                borderBottom: '1px solid var(--border-light)'
              }}>
                <h3 style={{ fontSize: '0.925rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                  Live 3-Way Comparative Trace
                </h3>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  Full LangGraph vs. Simple vs. Trivial
                </span>
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                gap: '1rem',
                alignItems: 'start',
                width: '100%'
              }}>
                {/* Column 1: Full Agent */}
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--brand-primary)', marginBottom: '0.5rem' }}>
                    ⚡ Full LangGraph Pipeline
                  </div>
                  {compareResults.full.error ? (
                    <div style={{ color: 'var(--status-danger)', fontSize: '0.78rem' }}>{compareResults.full.error}</div>
                  ) : (
                    <PipelineTrace result={compareResults.full} />
                  )}
                </div>

                {/* Column 2: Simple Baseline */}
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                    Simple Baseline (TF-IDF)
                  </div>
                  {compareResults.simple.error ? (
                    <div style={{ color: 'var(--status-danger)', fontSize: '0.78rem' }}>{compareResults.simple.error}</div>
                  ) : (
                    <PipelineTrace result={compareResults.simple} />
                  )}
                </div>

                {/* Column 3: Trivial Baseline */}
                <div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                    Trivial Baseline (Keyword Rule)
                  </div>
                  {compareResults.trivial.error ? (
                    <div style={{ color: 'var(--status-danger)', fontSize: '0.78rem' }}>{compareResults.trivial.error}</div>
                  ) : (
                    <PipelineTrace result={compareResults.trivial} />
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
