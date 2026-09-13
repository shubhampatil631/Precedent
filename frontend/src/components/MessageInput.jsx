import React, { useState } from 'react';
import { Send, Sparkles, Sliders, Check, Twitter, CheckCircle2, ChevronRight, ShieldAlert, LifeBuoy, CornerDownLeft } from 'lucide-react';

export default function MessageInput({
  onRun,
  loading,
  selectedSystem,
  setSelectedSystem,
  compareBaselines,
  setCompareBaselines
}) {
  const [text, setText] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [selectedScenarioIdx, setSelectedScenarioIdx] = useState(null);

  const sampleScenarios = [
    {
      category: 'resolution',
      label: 'Baggage Missing on Arrival',
      intent: 'baggage_luggage_issues',
      badge: 'Auto-Handle',
      text: '@AmericanAir landed in MIA on flight AA102 but my checked bag didn\'t show up on carousel 4. How do I file a lost bag claim?'
    },
    {
      category: 'resolution',
      label: 'Flight Delay Rebooking',
      intent: 'flight_delay_cancellation',
      badge: 'Auto-Handle',
      text: '@AmericanAir my connecting flight AA1234 from DFW to ORD got cancelled with no rebooking. What are my options to reach Chicago tonight?'
    },
    {
      category: 'resolution',
      label: 'In-Flight Wi-Fi Query',
      intent: 'seat_cabin_comfort',
      badge: 'Auto-Handle',
      text: '@AmericanAir how do I connect to the high speed Viasat satellite wifi on my flight to Boston?'
    },
    {
      category: 'safety',
      label: '🚨 Cabin Safety Emergency',
      intent: 'safety_legal_escalation',
      badge: 'Escalate',
      text: '@AmericanAir there is heavy smoke coming from the overhead bin in row 14 on flight 404, we need emergency support immediately!'
    },
    {
      category: 'safety',
      label: '⚖️ Legal Threat & Litigation',
      intent: 'safety_legal_escalation',
      badge: 'Escalate',
      text: '@AmericanAir your agent assaulted me and breached contract. I am instructing my attorney to file a federal lawsuit today unless I am refunded.'
    },
    {
      category: 'safety',
      label: '💳 Double Billing Dispute',
      intent: 'refund_compensation_claims',
      badge: 'Escalate',
      text: '@AmericanAir you charged my credit card twice for $450 without authorization for confirmation #X7KZ9. Reverse this fraudulent charge immediately.'
    },
    {
      category: 'edge',
      label: 'Off-Topic Recipe Question',
      intent: 'other_unclear',
      badge: 'Edge Case',
      text: '@AmericanAir what is the best temperature and recipe to bake a chocolate banana cake with pineapples?'
    },
    {
      category: 'edge',
      label: 'Vague One-Word Greeting',
      intent: 'other_unclear',
      badge: 'Edge Case',
      text: '@AmericanAir hello ???'
    }
  ];

  const filteredScenarios = activeCategory === 'all'
    ? sampleScenarios
    : sampleScenarios.filter(s => s.category === activeCategory);

  const handleSelectScenario = (scenario, idx) => {
    setText(scenario.text);
    setSelectedScenarioIdx(idx);
  };

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (text.trim() && !loading) {
      onRun(text.trim());
    }
  };

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      handleSubmit();
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '1.25rem',
      width: '100%'
    }}>
      {/* Input Header & Architecture Switcher (Fluid, Non-Boxy) */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div style={{
            width: '24px',
            height: '24px',
            borderRadius: '50%',
            background: '#1d9bf0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            flexShrink: 0
          }}>
            <Twitter size={13} fill="#ffffff" />
          </div>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Customer Tweet Intake
          </span>
        </div>

        {/* Seamless Control Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => setCompareBaselines(!compareBaselines)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              padding: '4px 9px',
              borderRadius: '6px',
              fontSize: '0.73rem',
              fontWeight: 600,
              background: compareBaselines ? 'var(--brand-subtle)' : 'transparent',
              color: compareBaselines ? 'var(--brand-primary)' : 'var(--text-secondary)',
              border: `1px solid ${compareBaselines ? 'var(--brand-border)' : 'transparent'}`,
              transition: 'all 0.15s ease'
            }}
          >
            <Sliders size={12} />
            <span>3-Way Compare</span>
            {compareBaselines && <Check size={12} strokeWidth={3} />}
          </button>

          {!compareBaselines && (
            <div style={{
              display: 'flex',
              background: 'var(--bg-surface-subtle)',
              padding: '2px',
              borderRadius: '6px'
            }}>
              {[
                { id: 'full', label: '⚡ LangGraph' },
                { id: 'simple', label: 'TF-IDF' },
                { id: 'trivial', label: 'Keyword' }
              ].map((sys) => {
                const isActive = selectedSystem === sys.id;
                return (
                  <button
                    key={sys.id}
                    type="button"
                    onClick={() => setSelectedSystem(sys.id)}
                    style={{
                      padding: '3px 8px',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      background: isActive ? '#ffffff' : 'transparent',
                      color: isActive ? 'var(--brand-primary)' : 'var(--text-muted)',
                      boxShadow: isActive ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
                      transition: 'all 0.12s ease'
                    }}
                  >
                    {sys.label}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Modern Fluid Composer with Integrated Action Bar */}
      <div style={{
        background: '#ffffff',
        borderRadius: '10px',
        border: '1px solid var(--border-default)',
        boxShadow: 'var(--shadow-card)',
        overflow: 'hidden',
        transition: 'border-color 0.15s ease, box-shadow 0.15s ease'
      }}>
        <textarea
          rows={3}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setSelectedScenarioIdx(null);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Type or select a customer tweet (@AmericanAir my flight got delayed...)"
          style={{
            width: '100%',
            padding: '0.75rem 0.85rem',
            background: 'transparent',
            border: 'none',
            fontSize: '0.84rem',
            lineHeight: '1.45',
            color: 'var(--text-primary)',
            outline: 'none',
            resize: 'none'
          }}
        />

        {/* Integrated Composer Footer */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0.45rem 0.75rem',
          background: 'var(--bg-surface-subtle)',
          borderTop: '1px solid var(--border-light)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            <span>{text.length} chars</span>
            <span>•</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
              <kbd style={{ padding: '1px 4px', borderRadius: '3px', background: '#ffffff', border: '1px solid var(--border-default)', fontFamily: 'var(--font-mono)', fontSize: '0.65rem' }}>Ctrl</kbd>+<kbd style={{ padding: '1px 4px', borderRadius: '3px', background: '#ffffff', border: '1px solid var(--border-default)', fontFamily: 'var(--font-mono)', fontSize: '0.65rem' }}>Enter</kbd>
            </span>
            {text.trim() && (
              <button
                type="button"
                onClick={() => { setText(''); setSelectedScenarioIdx(null); }}
                style={{ color: 'var(--text-muted)', textDecoration: 'underline', fontSize: '0.7rem', marginLeft: '0.25rem' }}
              >
                Clear
              </button>
            )}
          </div>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading || !text.trim()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              padding: '0.45rem 1rem',
              borderRadius: '6px',
              background: loading || !text.trim() ? '#cbd5e1' : 'var(--brand-primary)',
              color: '#ffffff',
              fontWeight: 700,
              fontSize: '0.78rem',
              boxShadow: '0 1px 3px rgba(37, 99, 235, 0.2)',
              transition: 'all 0.15s ease'
            }}
          >
            {loading ? (
              <span>Running...</span>
            ) : (
              <>
                <Send size={13} />
                <span>Execute Agent</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Preset Scenarios (Sleek Streamlined Tag Cloud) */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.35rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
            <Sparkles size={12} color="var(--brand-primary)" />
            <span>Preset Test Scenarios</span>
          </div>

          {/* Minimalist Filter Tabs */}
          <div style={{ display: 'flex', gap: '0.2rem' }}>
            {[
              { id: 'all', label: 'All' },
              { id: 'resolution', label: 'Resolvable' },
              { id: 'safety', label: 'Safety' },
              { id: 'edge', label: 'Edge' }
            ].map(tab => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveCategory(tab.id)}
                style={{
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '0.67rem',
                  fontWeight: 600,
                  background: activeCategory === tab.id ? 'var(--brand-subtle)' : 'transparent',
                  color: activeCategory === tab.id ? 'var(--brand-primary)' : 'var(--text-muted)',
                  transition: 'all 0.1s ease'
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Minimalist Scenario List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          {filteredScenarios.map((scenario, idx) => {
            const isSelected = text === scenario.text;
            const isEscalate = scenario.category === 'safety';

            return (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelectScenario(scenario, idx)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.45rem 0.65rem',
                  borderRadius: '6px',
                  background: isSelected ? 'var(--brand-subtle)' : '#ffffff',
                  border: isSelected ? '1px solid var(--brand-border)' : '1px solid transparent',
                  boxShadow: isSelected ? '0 1px 2px rgba(37, 99, 235, 0.08)' : '0 1px 2px rgba(0,0,0,0.02)',
                  color: isSelected ? 'var(--brand-primary)' : 'var(--text-primary)',
                  fontSize: '0.74rem',
                  fontWeight: isSelected ? 700 : 500,
                  textAlign: 'left',
                  transition: 'all 0.12s ease'
                }}
              >
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginRight: '0.5rem' }}>
                  {scenario.label}
                </span>
                <span style={{
                  fontSize: '0.62rem',
                  padding: '1px 5px',
                  borderRadius: '3px',
                  background: isEscalate ? 'var(--status-danger-bg)' : 'var(--bg-surface-subtle)',
                  color: isEscalate ? 'var(--status-danger-text)' : 'var(--text-muted)',
                  fontWeight: 700,
                  flexShrink: 0
                }}>
                  {scenario.badge}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
