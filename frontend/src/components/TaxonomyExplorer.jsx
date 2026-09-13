import React, { useEffect, useState } from 'react';
import { Tag, ShieldAlert, CheckCircle, Search, Layers, RefreshCw, AlertTriangle, MessageSquare, ChevronDown, ChevronUp, Sparkles, Filter } from 'lucide-react';
import { getTaxonomy } from '../api';

export default function TaxonomyExplorer() {
  const [taxonomy, setTaxonomy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterRisk, setFilterRisk] = useState('all');
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    fetchTaxonomy();
  }, []);

  const fetchTaxonomy = async () => {
    setLoading(true);
    try {
      const data = await getTaxonomy();
      setTaxonomy(data);
    } catch (e) {
      console.error('Failed to load taxonomy:', e);
    } finally {
      setLoading(false);
    }
  };

  const highRiskPatterns = ['safety', 'legal', 'refund', 'billing', 'emergency', 'complaint'];

  const defaultIntents = [
    {
      id: 'flight_delay_cancellation',
      label: 'Flight Delay or Cancellation',
      description: 'Customer reports a delayed, cancelled, diverted, or rescheduled flight and seeks status, connection help, or rebooking.',
      examples: [
        "@AmericanAir Flight AA2453 is delayed over 3 hours now. Will I make my connection in Charlotte?",
        "@AmericanAir our flight from ORD to DFW just got cancelled with no explanation. How do we get on the next flight?"
      ]
    },
    {
      id: 'baggage_luggage_issues',
      label: 'Baggage and Luggage Issues',
      description: 'Customer inquires about delayed, missing, lost, or damaged checked luggage, baggage claim procedures, or baggage fees.',
      examples: [
        "@AmericanAir landed in Miami but my bag never arrived on carousel 4. Where do I file a lost baggage claim?",
        "@AmericanAir - still no bags... they've been ofd since 9:30... This NYC trip is not going good at all."
      ]
    },
    {
      id: 'rebooking_ticket_changes',
      label: 'Flight Rebooking and Ticket Changes',
      description: 'Customer wants to change travel dates, switch flights, request standby, or modify passenger information on an existing ticket.',
      examples: [
        "@AmericanAir can I change my flight tomorrow to an earlier departure without paying change fees?",
        "@AmericanAir I need to add my infant in lap to my existing reservation. Can you help me do this?"
      ]
    },
    {
      id: 'seat_cabin_comfort',
      label: 'Seat Assignment and Amenities',
      description: 'Customer inquires about seat selection, upgrades, Main Cabin Extra, legroom, inflight Wi-Fi, or entertainment.',
      examples: [
        "@AmericanAir I booked seats together with my spouse but you separated us at check-in. Can you fix this?",
        "@AmericanAir wifi on flight AA890 is not working at all despite paying $15 for access."
      ]
    },
    {
      id: 'checkin_boarding_issues',
      label: 'Check-in and Airport Boarding',
      description: 'Customer encounters issues with online/mobile check-in, TSA PreCheck not showing on boarding pass, or airport gate boarding.',
      examples: [
        "@AmericanAir the app won't let me check in for my flight tomorrow. Keeps saying 'error loading boarding pass'.",
        "@AmericanAir my known traveler number was saved on my profile but TSA PreCheck is missing from my boarding pass."
      ]
    },
    {
      id: 'refund_compensation_claims',
      label: 'Refund, Voucher & Compensation Claims',
      description: 'Customer requests a ticket refund, compensation for delays/cancellations, or clarification on travel credit/vouchers (High risk financial).',
      examples: [
        "@AmericanAir I submitted a refund request two weeks ago for a cancelled flight. What is the status of my refund?",
        "@AmericanAir we were stuck overnight in Philadelphia due to mechanical delay. How do we claim hotel voucher compensation?"
      ]
    },
    {
      id: 'safety_legal_escalation',
      label: 'Safety, Security & Legal Escalation',
      description: 'Customer reports an in-flight safety hazard, medical emergency, security threat, or threatens legal/regulatory litigation (Mandatory human escalation).',
      examples: [
        "@AmericanAir this is gross negligence and breach of contract. I am contacting the FAA and my attorney immediately.",
        "@AmericanAir a passenger on flight AA302 is experiencing a medical emergency, emergency medical team needed at gate."
      ]
    },
    {
      id: 'frequent_flyer_loyalty',
      label: 'AAdvantage Loyalty and Miles',
      description: 'Customer asks about AAdvantage account balance, missing miles from past flights, loyalty status tiers, or partner airline points.',
      examples: [
        "@AmericanAir my miles for my flight last week to London haven't posted to my AAdvantage account yet.",
        "@AmericanAir how many loyalty points do I need before the end of the month to maintain Platinum status?"
      ]
    },
    {
      id: 'booking_reservation_inquiry',
      label: 'New Booking and Policy Inquiries',
      description: 'Customer has questions about booking policies, unaccompanied minors, pet travel policies, or payment methods on aa.com.',
      examples: [
        "@AmericanAir what is your current policy for traveling with a small dog in the cabin?",
        "@AmericanAir can I hold a reservation for 24 hours before finalizing payment?"
      ]
    },
    {
      id: 'customer_service_complaint',
      label: 'Customer Service & Staff Feedback',
      description: 'Customer expresses dissatisfaction with rude staff, phone hold times, lack of communication, or poor customer support experience.',
      examples: [
        "@AmericanAir been on hold on your customer service line for 2 and a half hours. This is completely unacceptable.",
        "@AmericanAir your gate agent in Charlotte was extremely rude and unhelpful to passengers seeking information."
      ]
    },
    {
      id: 'praise_feedback_gratitude',
      label: 'Praise, Gratitude and Compliments',
      description: 'Customer thanks the airline, flight attendants, or pilots for exceptional service or a great travel experience.',
      examples: [
        "@AmericanAir huge shoutout to flight attendant Sarah on AA450 today for being so attentive and kind!",
        "@AmericanAir smooth flight and arrived 20 minutes early into Chicago. Great job team!"
      ]
    },
    {
      id: 'other_unclear',
      label: 'Other or Unclear / Out of Domain',
      description: 'Inquiries that are ambiguous, unintelligible, brief greetings/pleasantries, or do not fit defined operational categories.',
      examples: [
        "@AmericanAir hello",
        "@AmericanAir ???"
      ]
    }
  ];

  const rawIntents = (taxonomy?.intents && taxonomy.intents.length > 0) ? taxonomy.intents : defaultIntents;

  const normalizedIntents = rawIntents.map(item => {
    const id = item.id || item.name || item.intent || '';
    const label = item.label || item.name || id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    const isHighRisk = highRiskPatterns.some(p => id.toLowerCase().includes(p));
    return {
      id,
      label,
      description: item.description || `Customer inquiries classified into cluster ${id}`,
      examples: item.examples || [],
      risk: isHighRisk ? 'high_risk' : 'normal'
    };
  });

  const filtered = normalizedIntents.filter(item => {
    const q = search.toLowerCase().trim();
    const matchesSearch = !q ||
      item.id.toLowerCase().includes(q) ||
      item.label.toLowerCase().includes(q) ||
      item.description.toLowerCase().includes(q) ||
      item.examples.some(ex => ex.toLowerCase().includes(q));

    if (filterRisk === 'high_risk') return matchesSearch && item.risk === 'high_risk';
    if (filterRisk === 'normal') return matchesSearch && item.risk === 'normal';
    return matchesSearch;
  });

  const highRiskCount = normalizedIntents.filter(i => i.risk === 'high_risk').length;
  const normalCount = normalizedIntents.filter(i => i.risk === 'normal').length;

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
      {/* Header Bar (Un-Boxy) */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem',
        paddingBottom: '0.25rem'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.2 }}>
              12-Intent Taxonomy Catalog
            </h2>
            <span style={{
              fontSize: '0.68rem',
              padding: '1px 6px',
              borderRadius: '4px',
              background: 'var(--brand-subtle)',
              color: 'var(--brand-primary)',
              fontWeight: 700
            }}>
              Optimal K = {taxonomy?.optimal_k || 11}
            </span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginTop: '2px' }}>
            Discovered via KMeans clustering on 10,000+ customer support tweets with deterministic policy routing.
          </p>
        </div>

        {/* Search & Filter Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', flexWrap: 'wrap' }}>
          {/* Search Box */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
            background: '#ffffff',
            border: '1px solid var(--border-default)',
            borderRadius: '6px',
            padding: '4px 9px',
            width: '180px',
            boxShadow: 'var(--shadow-xs)'
          }}>
            <Search size={12} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Filter intents..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                border: 'none',
                background: 'transparent',
                outline: 'none',
                fontSize: '0.75rem',
                color: 'var(--text-primary)',
                width: '100%'
              }}
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch('')}
                style={{ fontSize: '0.68rem', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                ✕
              </button>
            )}
          </div>

          {/* Risk Level Segmented Buttons */}
          <div style={{
            display: 'flex',
            background: 'var(--bg-surface-subtle)',
            padding: '2px',
            borderRadius: '6px'
          }}>
            {[
              { id: 'all', label: `All (${normalizedIntents.length})` },
              { id: 'normal', label: `Auto-Handle (${normalCount})` },
              { id: 'high_risk', label: `Escalate (${highRiskCount})` }
            ].map(tab => {
              const isActive = filterRisk === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setFilterRisk(tab.id)}
                  style={{
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    background: isActive ? '#ffffff' : 'transparent',
                    color: isActive
                      ? (tab.id === 'high_risk' ? 'var(--status-danger)' : 'var(--brand-primary)')
                      : 'var(--text-muted)',
                    boxShadow: isActive ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
                    transition: 'all 0.12s ease'
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Grid of Intent Cards (Modern, Clean, Soft elevation) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(310px, 1fr))',
        gap: '0.85rem',
        width: '100%'
      }}>
        {filtered.map((item, idx) => {
          const isHighRisk = item.risk === 'high_risk';
          const isExpanded = expandedId === item.id;

          return (
            <div
              key={item.id || idx}
              style={{
                background: '#ffffff',
                borderRadius: '10px',
                padding: '0.9rem 1rem',
                border: '1px solid var(--border-default)',
                boxShadow: 'var(--shadow-card)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                gap: '0.75rem',
                transition: 'border-color 0.15s ease, box-shadow 0.15s ease'
              }}
            >
              <div>
                {/* Title & Badge */}
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.35rem', gap: '0.4rem' }}>
                  <div>
                    <h3 style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.25 }}>
                      {item.label}
                    </h3>
                    <div style={{
                      fontSize: '0.68rem',
                      fontWeight: 600,
                      fontFamily: 'var(--font-mono)',
                      color: isHighRisk ? 'var(--status-danger)' : 'var(--brand-primary)',
                      marginTop: '1px'
                    }}>
                      {item.id}
                    </div>
                  </div>

                  <span style={{
                    fontSize: '0.62rem',
                    padding: '1px 5px',
                    borderRadius: '4px',
                    fontWeight: 700,
                    background: isHighRisk ? 'var(--status-danger-bg)' : 'var(--status-success-bg)',
                    color: isHighRisk ? 'var(--status-danger-text)' : 'var(--status-success-text)',
                    whiteSpace: 'nowrap'
                  }}>
                    {isHighRisk ? 'Escalate' : 'Auto-Handle'}
                  </span>
                </div>

                <p style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.4, marginBottom: '0.4rem' }}>
                  {item.description}
                </p>

                {/* Sample Tweets Accordion */}
                {item.examples && item.examples.length > 0 && (
                  <div style={{ marginTop: '0.25rem' }}>
                    <button
                      type="button"
                      onClick={() => setExpandedId(isExpanded ? null : item.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        color: 'var(--brand-primary)',
                        padding: '2px 5px',
                        borderRadius: '4px',
                        background: 'var(--brand-subtle)'
                      }}
                    >
                      <MessageSquare size={10} />
                      <span>{isExpanded ? 'Hide' : `View ${item.examples.length} Examples`}</span>
                      {isExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                    </button>

                    {isExpanded && (
                      <div style={{
                        marginTop: '0.4rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.25rem',
                        background: 'var(--bg-app)',
                        padding: '0.5rem',
                        borderRadius: '6px'
                      }}>
                        {item.examples.map((ex, i) => (
                          <div key={i} style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontStyle: 'italic', lineHeight: 1.35 }}>
                            • "{ex}"
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Policy Action Strip */}
              <div style={{
                background: 'var(--bg-surface-subtle)',
                borderRadius: '6px',
                padding: '5px 8px',
                fontSize: '0.7rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <span style={{ color: 'var(--text-muted)' }}>Policy:</span>
                <strong style={{ color: isHighRisk ? 'var(--status-danger)' : 'var(--status-success-text)' }}>
                  {isHighRisk ? 'Human Escalation' : 'Precedent Grounded Reply'}
                </strong>
              </div>
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div style={{
          background: '#ffffff',
          borderRadius: '10px',
          border: '1px dashed var(--border-default)',
          padding: '2.5rem',
          textAlign: 'center',
          color: 'var(--text-muted)'
        }}>
          <p style={{ fontSize: '0.8rem' }}>No intent clusters matched your search query.</p>
          <button
            type="button"
            onClick={() => { setSearch(''); setFilterRisk('all'); }}
            style={{
              marginTop: '0.4rem',
              color: 'var(--brand-primary)',
              fontWeight: 600,
              fontSize: '0.75rem',
              textDecoration: 'underline'
            }}
          >
            Reset all filters
          </button>
        </div>
      )}
    </div>
  );
}
