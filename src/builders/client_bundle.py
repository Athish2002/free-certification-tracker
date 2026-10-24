"""
Client bundle generator for CertPulse web application.
Compiles interactive state controllers, SVG icon bank, Proof Modal accessibility handlers,
multi-view render engines (Grid, Table, Timeline, Matrix, Redemption), and 4-timezone world telemetry.
"""

from typing import Dict, Any, List
import json

JS_TEMPLATE = """
        const offersData = __OFFERS_DATA__;
        const newsData = __NEWS_DATA__;
        const LAST_SYNC_ISO = "__LAST_SYNC_ISO__";

        let currentMainTab = 'vouchers';
        let currentTier = 'all';
        let currentCategory = 'All';
        let currentSearch = '';
        let currentLayout = 'grid';

        function filterTier(tier) {
            currentTier = tier;
            document.querySelectorAll('#tierFilterPills .tier-pill').forEach(btn => {
                if (btn.getAttribute('data-tier') === tier) {
                    btn.style.backgroundColor = 'var(--accent-emphasis)';
                    btn.style.color = '#ffffff';
                    btn.classList.add('font-semibold');
                    btn.classList.remove('font-medium');
                } else {
                    btn.style.backgroundColor = 'var(--canvas-default)';
                    btn.style.color = 'var(--fg-muted)';
                    btn.classList.remove('font-semibold');
                    btn.classList.add('font-medium');
                }
            });
            renderCards();
        }

        // Accessible Screenshot Proof Lightbox Modal Engine
        let previousActiveElement = null;

        function openProofModal(id) {
            const offer = offersData.find(o => o.id === id);
            if (!offer) return;

            previousActiveElement = document.activeElement;

            const modal = document.getElementById('proofModal');
            const titleEl = document.getElementById('proofModalTitle');
            const platformEl = document.getElementById('proofModalPlatform');
            const tierEl = document.getElementById('proofModalTier');
            const badgeEl = document.getElementById('proofModalBadge');
            const alertEl = document.getElementById('proofModalAlert');
            const capturedAtEl = document.getElementById('proofModalCapturedAt');
            const dateEl = document.getElementById('proofModalDate');
            const termsEl = document.getElementById('proofModalTerms');
            const portalLink = document.getElementById('proofModalPortalLink');
            const directLink = document.getElementById('proofModalDirectLink');
            const img = document.getElementById('proofModalImage');
            const fallback = document.getElementById('proofImageFallback');
            const fallbackPath = document.getElementById('proofFallbackPath');

            if (titleEl) titleEl.textContent = offer.title || offer.certification_name || '';
            if (platformEl) platformEl.textContent = offer.platform || '';

            // 4-Timezone timestamp representation for global verification
            const rawDate = (offer.visual_proof && offer.visual_proof.captured_at) || offer.verification_date || '';
            let dateDisplay = rawDate;
            let multiTzCaptured = rawDate;
            if (rawDate) {
                const dt = new Date(rawDate);
                if (Number.isFinite(dt.getTime())) {
                    const utcStr = dt.toLocaleString('en-US', { timeZone: 'UTC', hour12: false, month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) + ' UTC';
                    const istStr = dt.toLocaleString('en-US', { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit' }) + ' IST';
                    const etStr = dt.toLocaleString('en-US', { timeZone: 'America/New_York', hour12: false, hour: '2-digit', minute: '2-digit' }) + ' EDT';
                    const cetStr = dt.toLocaleString('en-US', { timeZone: 'Europe/Berlin', hour12: false, hour: '2-digit', minute: '2-digit' }) + ' CEST';
                    dateDisplay = `${utcStr} (${istStr} • ${etStr} • ${cetStr})`;
                    multiTzCaptured = `${utcStr} • ${istStr} • ${etStr} • ${cetStr}`;
                }
            }
            if (dateEl) dateEl.textContent = dateDisplay ? ('Audited: ' + dateDisplay) : '';
            if (capturedAtEl) capturedAtEl.textContent = multiTzCaptured || 'Verified';

            const isProctored = offer.credential_tier === 'proctored_exam' || offer.credential_tier === 'primary';
            const tierLabel = isProctored ? '🎓 Written Proctored Exam' : '🎖️ Skill Badge & Lab';
            
            if (tierEl) {
                tierEl.textContent = tierLabel;
                if (isProctored) {
                    tierEl.style.backgroundColor = 'var(--accent-subtle)';
                    tierEl.style.borderColor = 'var(--accent-fg)';
                    tierEl.style.color = 'var(--accent-fg)';
                } else {
                    tierEl.style.backgroundColor = 'var(--canvas-inset)';
                    tierEl.style.borderColor = 'var(--border-default)';
                    tierEl.style.color = 'var(--fg-muted)';
                }
            }

            const status = offer.status || 'Active';

            if (status === 'Active') {
                if (alertEl) alertEl.classList.add('hidden');
                if (badgeEl) {
                    badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-bold border';
                    badgeEl.style.backgroundColor = 'var(--success-subtle)';
                    badgeEl.style.borderColor = 'var(--success-fg)';
                    badgeEl.style.color = 'var(--success-fg)';
                    badgeEl.textContent = '🟢 $0.00 Verified Active Terms';
                }
                if (termsEl) {
                    termsEl.style.color = 'var(--success-fg)';
                    termsEl.textContent = offer.cart_balance_verified || '$0.00 Confirmed Zero-Dollar Waiver';
                }
                if (portalLink) {
                    portalLink.className = 'px-3.5 py-1.5 rounded-lg text-white font-semibold transition active:scale-[0.98] inline-flex items-center gap-1.5 cursor-pointer shadow-xs';
                    portalLink.style.backgroundColor = 'var(--btn-primary-bg)';
                    portalLink.style.borderColor = '';
                    portalLink.style.color = '#ffffff';
                    portalLink.innerHTML = '<span>Launch Official Portal</span><svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M3.75 2h3.5a.75.75 0 0 1 0 1.5h-3.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-3.5a.75.75 0 0 1 1.5 0v3.5A1.75 1.75 0 0 1 12.25 14h-8.5A1.75 1.75 0 0 1 2 12.25v-8.5C2 2.784 2.784 2 3.75 2Zm6.75.75a.75.75 0 0 1 .75-.75h3.5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0V4.56L8.53 10.03a.75.75 0 0 1-1.06-1.06l5.47-5.47H11.25a.75.75 0 0 1-.75-.75Z"></path></svg>';
                }
            } else if (status === 'Broken Link') {
                if (alertEl) {
                    alertEl.classList.remove('hidden');
                    alertEl.className = 'px-4 sm:px-6 py-2.5 text-xs border-b flex items-start gap-2 bg-red-500/10 border-red-500/20 text-red-500 font-medium';
                    alertEl.innerHTML = '<span class="text-sm">⚠️</span><span><strong>Broken Link / Inaccessible Portal:</strong> The tracked URL returned an HTTP 404 or dead-end during our automated audit. The screenshot proof below records this exact failure state. This offer is quarantined in Triage and is NOT active.</span>';
                }
                if (badgeEl) {
                    badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-bold border border-red-500/30 bg-red-500/20 text-red-500';
                    badgeEl.style.backgroundColor = '';
                    badgeEl.style.borderColor = '';
                    badgeEl.style.color = '';
                    badgeEl.textContent = '⚠️ Broken Link (HTTP 404)';
                }
                if (termsEl) {
                    termsEl.style.color = '#ef4444';
                    termsEl.textContent = 'Verification Failed — HTTP 404 / Dead-End';
                }
                if (portalLink) {
                    portalLink.className = 'px-3.5 py-1.5 rounded-lg border font-semibold transition inline-flex items-center gap-1.5 cursor-pointer opacity-75';
                    portalLink.style.backgroundColor = 'var(--btn-default-bg)';
                    portalLink.style.borderColor = 'var(--border-default)';
                    portalLink.style.color = 'var(--fg-default)';
                    portalLink.innerHTML = '<span>Inspect Failing Portal</span>';
                }
            } else if (status === 'Registrations Closed') {
                if (alertEl) {
                    alertEl.classList.remove('hidden');
                    alertEl.className = 'px-4 sm:px-6 py-2.5 text-xs border-b flex items-start gap-2 bg-amber-500/10 border-amber-500/20 text-amber-500 font-medium';
                    alertEl.innerHTML = '<span class="text-sm">🟡</span><span><strong>Registrations Closed:</strong> The vendor has closed registrations or cohort capacity has been reached. The screenshot below captures the official closure notice. Quarantined in Triage until vendor reopens.</span>';
                }
                if (badgeEl) {
                    badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-bold border border-amber-500/30 bg-amber-500/20 text-amber-500';
                    badgeEl.style.backgroundColor = '';
                    badgeEl.style.borderColor = '';
                    badgeEl.style.color = '';
                    badgeEl.textContent = '🟡 Closed / Waitlist';
                }
                if (termsEl) {
                    termsEl.style.color = '#f59e0b';
                    termsEl.textContent = 'Cohort Capacity Reached or Registrations Concluded';
                }
                if (portalLink) {
                    portalLink.className = 'px-3.5 py-1.5 rounded-lg border font-semibold transition inline-flex items-center gap-1.5 cursor-pointer';
                    portalLink.style.backgroundColor = 'var(--btn-default-bg)';
                    portalLink.style.borderColor = 'var(--border-default)';
                    portalLink.style.color = 'var(--fg-default)';
                    portalLink.innerHTML = '<span>Inspect Vendor Portal</span>';
                }
            } else if (status === 'Review Needed') {
                if (alertEl) {
                    alertEl.classList.remove('hidden');
                    alertEl.className = 'px-4 sm:px-6 py-2.5 text-xs border-b flex items-start gap-2 bg-amber-500/10 border-amber-500/20 text-amber-500 font-medium';
                    alertEl.innerHTML = '<span class="text-sm">🟡</span><span><strong>Under Review (Triage Pool):</strong> Affirmative zero-dollar waiver terms could not be confirmed in the rendered DOM. Quarantined in Triage until verified.</span>';
                }
                if (badgeEl) {
                    badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-bold border border-amber-500/30 bg-amber-500/20 text-amber-500';
                    badgeEl.style.backgroundColor = '';
                    badgeEl.style.borderColor = '';
                    badgeEl.style.color = '';
                    badgeEl.textContent = '🟡 Under Review (Triage)';
                }
                if (termsEl) {
                    termsEl.style.color = '#f59e0b';
                    termsEl.textContent = offer.inspection_notes || 'Pending Affirmative Zero-Dollar Waiver Terms';
                }
                if (portalLink) {
                    portalLink.className = 'px-3.5 py-1.5 rounded-lg border font-semibold transition inline-flex items-center gap-1.5 cursor-pointer';
                    portalLink.style.backgroundColor = 'var(--btn-default-bg)';
                    portalLink.style.borderColor = 'var(--border-default)';
                    portalLink.style.color = 'var(--fg-default)';
                    portalLink.innerHTML = '<span>Inspect Vendor Portal</span>';
                }
            } else if (status === 'Server Error') {
                if (alertEl) {
                    alertEl.classList.remove('hidden');
                    alertEl.className = 'px-4 sm:px-6 py-2.5 text-xs border-b flex items-start gap-2 bg-red-500/10 border-red-500/20 text-red-500 font-medium';
                    alertEl.innerHTML = '<span class="text-sm">⚠️</span><span><strong>Server Error (HTTP 500):</strong> The vendor server failed to respond or is down for maintenance. Quarantined in Triage.</span>';
                }
                if (badgeEl) {
                    badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-bold border border-red-500/30 bg-red-500/20 text-red-500';
                    badgeEl.style.backgroundColor = '';
                    badgeEl.style.borderColor = '';
                    badgeEl.style.color = '';
                    badgeEl.textContent = '⚠️ Server Error (HTTP 500)';
                }
                if (termsEl) {
                    termsEl.style.color = '#ef4444';
                    termsEl.textContent = 'Host Down / Gateway Error';
                }
                if (portalLink) {
                    portalLink.className = 'px-3.5 py-1.5 rounded-lg border font-semibold transition inline-flex items-center gap-1.5 cursor-pointer opacity-75';
                    portalLink.style.backgroundColor = 'var(--btn-default-bg)';
                    portalLink.style.borderColor = 'var(--border-default)';
                    portalLink.style.color = 'var(--fg-default)';
                    portalLink.innerHTML = '<span>Inspect Server Status</span>';
                }
            } else {
                if (alertEl) alertEl.classList.add('hidden');
                if (badgeEl) {
                    badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-bold border border-slate-500/30 bg-slate-500/20 text-slate-400';
                    badgeEl.style.backgroundColor = '';
                    badgeEl.style.borderColor = '';
                    badgeEl.style.color = '';
                    badgeEl.textContent = '📜 Historical Archive';
                }
                if (termsEl) {
                    termsEl.style.color = 'var(--fg-muted)';
                    termsEl.textContent = 'Concluded Campaign (Preserved for Recurrence Tracking)';
                }
                if (portalLink) {
                    portalLink.className = 'px-3.5 py-1.5 rounded-lg border font-semibold transition inline-flex items-center gap-1.5 cursor-pointer';
                    portalLink.style.backgroundColor = 'var(--btn-default-bg)';
                    portalLink.style.borderColor = 'var(--border-default)';
                    portalLink.style.color = 'var(--fg-default)';
                    portalLink.innerHTML = '<span>Inspect Archive Portal</span>';
                }
            }

            // Truth Oracle online policy corroboration wiring
            const tv = offer.truth_verification;
            const truthCard = document.getElementById('proofModalTruthCard');
            const policyTypeEl = document.getElementById('proofModalPolicyType');
            const sourceNameEl = document.getElementById('proofModalTruthSourceName');
            const sourceLink = document.getElementById('proofModalTruthSource');
            const notesEl = document.getElementById('proofModalTruthNotes');

            if (tv) {
                if (truthCard) truthCard.classList.remove('hidden');
                if (policyTypeEl) {
                    policyTypeEl.textContent = (tv.policy_type || 'VERIFIED').replace(/_/g, ' ').replace(/\\b100pct\\b/gi, '100%').toUpperCase();
                    if (tv.policy_type === 'verified_100pct_free') {
                        policyTypeEl.className = 'px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-500 border border-emerald-500/30';
                    } else if (tv.policy_type === 'partial_discount_copay' || tv.policy_type === 'annual_window_closed') {
                        policyTypeEl.className = 'px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-500 border border-amber-500/30';
                    } else {
                        policyTypeEl.className = 'px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-500/10 text-slate-500 border border-slate-500/30';
                    }
                }
                if (sourceNameEl) sourceNameEl.textContent = tv.truth_source_name || offer.platform;
                if (sourceLink) sourceLink.href = tv.truth_source_url || offer.url;
                if (notesEl) notesEl.textContent = tv.verdict_notes || '';

                if (tv.policy_type === 'partial_discount_copay' && tv.real_exam_cost_usd > 0) {
                    if (alertEl) {
                        alertEl.classList.remove('hidden');
                        alertEl.className = 'px-4 sm:px-6 py-2.5 text-xs border-b flex items-start gap-2 bg-amber-500/10 border-amber-500/20 text-amber-500 font-medium';
                        alertEl.innerHTML = '<span class="text-sm">⚠️</span><span><strong>Official ' + tv.verified_discount_pct + '% Discount Voucher:</strong> This voucher covers ' + tv.verified_discount_pct + '% of the examination fee. The candidate must pay the remaining co-pay fee of ~$' + tv.real_exam_cost_usd.toFixed(2) + ' USD at Pearson VUE checkout. It is NOT a $0.00 waiver.</span>';
                    }
                }
            } else if (truthCard) {
                truthCard.classList.add('hidden');
            }

            const targetLaunchUrl = offer.direct_verified_url || offer.verified_vendor_url || offer.url || '#';
            if (portalLink) portalLink.href = targetLaunchUrl;
            if (directLink) directLink.href = targetLaunchUrl;

            const shotPath = offer.screenshot_path 
                ? (offer.screenshot_path.startsWith('docs/') ? './' + offer.screenshot_path.slice(5) : './' + offer.screenshot_path)
                : ('./screenshots/' + offer.id + '.png');

            if (fallback) fallback.classList.add('hidden');
            if (img) {
                img.classList.remove('hidden');
                img.src = shotPath;
                img.onerror = function() {
                    const rawFallback = 'https://raw.githubusercontent.com/Athish2002/free-certification-tracker/main/docs/screenshots/' + offer.id + '.png';
                    if (img.src !== rawFallback) {
                        img.src = rawFallback;
                    } else {
                        img.classList.add('hidden');
                        if (fallback) {
                            fallback.classList.remove('hidden');
                            if (fallbackPath) fallbackPath.textContent = 'docs/screenshots/' + offer.id + '.png';
                        }
                    }
                };
            }

            if (modal) {
                modal.classList.remove('hidden');
                document.body.style.overflow = 'hidden';
                const closeBtn = document.getElementById('closeProofModalBtn');
                if (closeBtn) closeBtn.focus();
            }
        }

        function closeProofModal() {
            const modal = document.getElementById('proofModal');
            if (modal && !modal.classList.contains('hidden')) {
                modal.classList.add('hidden');
                document.body.style.overflow = '';
                if (previousActiveElement && typeof previousActiveElement.focus === 'function') {
                    previousActiveElement.focus();
                }
            }
        }

        function handleProofModalBackdrop(e) {
            if (e.target.id === 'proofModal') {
                closeProofModal();
            }
        }

        function closeProofModalOnBackdrop(e) {
            handleProofModalBackdrop(e);
        }
        
        let currentNewsCategory = 'All';
        let currentNewsSearch = '';

        // Checked Offers Goal Storage
        let checkedOfferIds = [];
        try {
            checkedOfferIds = JSON.parse(localStorage.getItem('certpulse_checked_offers') || '[]');
        } catch(e) {
            checkedOfferIds = [];
        }

        // Authentic Brand Logos (SVG Vector Library for 22+ platforms)
        function getPlatformIconSvg(platform) {
            if (!platform) return '';
            const p = platform.toLowerCase();
            if (p.includes('aws') || p.includes('amazon')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#ff9900"><path d="M4 11.5c3.5 1.8 7.5.8 9.5-.5.3-.2.5.2.3.4-1.8 1.8-6.5 2.8-9.8.7-.3-.2 0-.6 0-.6zm8.8-1.7c-.2-.3-1.4-.4-2-.3-.2 0-.2-.2 0-.3.7-.5 2.1-.3 2.3 0 .2.2.1 1.6-.5 2.1-.2.2-.3.1-.3 0 .1-.5.7-1.2.5-1.5z"/><path d="M10.7 7.2c-.1-.7-.4-1.3-1-1.7-.8-.5-1.9-.5-2.6 0-.6.4-.9 1-.9 1.7 0 .5.3 1 .8 1.3.7.4 1.7.5 2.6.2.8-.3 1.1-.9 1.1-1.5zm-3.3 0c0-.4.2-.7.6-.9.4-.2.9-.2 1.3 0 .4.2.6.5.6.9 0 .4-.2.7-.6.9-.4.2-.9.2-1.3 0-.4-.2-.6-.5-.6-.9z"/></svg>`;
            }
            if (p.includes('azure') || p.includes('microsoft')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><rect x="1" y="1" width="6.5" height="6.5" fill="#f25022"/><rect x="8.5" y="1" width="6.5" height="6.5" fill="#7fba00"/><rect x="1" y="8.5" width="6.5" height="6.5" fill="#00a4ef"/><rect x="8.5" y="8.5" width="6.5" height="6.5" fill="#ffb900"/></svg>`;
            }
            if (p.includes('google')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><path d="M10.2 4.4A3.8 3.8 0 0 0 4 6.2a3 3 0 0 0-2 2.8 3 3 0 0 0 3 3h7.5a3 3 0 0 0 3-3 3 3 0 0 0-2.5-3 3.8 3.8 0 0 0-2.8-1.6z" fill="#4285f4"/><path d="M10.2 4.4a3.8 3.8 0 0 0-3.5 2.4l1.8 1.8a2 2 0 0 1 1.7-1.2 2 2 0 0 1 2 2l1.3-.3a3 3 0 0 0-3.3-4.7z" fill="#ea4335"/><path d="M13 9a3 3 0 0 1-3 3H5a3 3 0 0 1-1.8-.6l1.2-1.2a2 2 0 0 0 .6.3h5a2 2 0 0 0 2-2z" fill="#34a853"/><path d="M2 9a3 3 0 0 1 3-3l1 1a2 2 0 0 0-2 2z" fill="#fbbc05"/></svg>`;
            }
            if (p.includes('oracle')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><rect x="1" y="3.5" width="14" height="9" rx="4.5" fill="#f80000"/><rect x="3.5" y="5.5" width="9" height="5" rx="2.5" fill="var(--canvas-subtle)"/></svg>`;
            }
            if (p.includes('cisco')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#1ba0d7"><rect x="1" y="7" width="1.5" height="6" rx="0.75"/><rect x="3.5" y="4" width="1.5" height="9" rx="0.75"/><rect x="6" y="8" width="1.5" height="5" rx="0.75"/><rect x="8.5" y="8" width="1.5" height="5" rx="0.75"/><rect x="11" y="4" width="1.5" height="9" rx="0.75"/><rect x="13.5" y="7" width="1.5" height="6" rx="0.75"/></svg>`;
            }
            if (p.includes('github')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"/></svg>`;
            }
            if (p.includes('linux') || p.includes('cncf')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><path d="M8 1l5.5 3.2v6.4L8 13.8l-5.5-3.2V4.2L8 1z" stroke="#326ce5" stroke-width="1.4" fill="none"/><circle cx="8" cy="7.5" r="2.5" fill="#326ce5"/></svg>`;
            }
            if (p.includes('databricks')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#ff3621"><path d="M8 1L2 4.5l6 3.5 6-3.5L8 1zm0 5L2 9.5l6 3.5 6-3.5L8 6zm0 5l-6 3.5 6 3.5 6-3.5L8 11z"/></svg>`;
            }
            if (p.includes('snowflake')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><path d="M8 1v14M1 8h14M3 3l10 10M3 13L13 3M6 2l2 2 2-2M6 14l2-2 2 2M2 6l2 2-2 2M14 6l-2 2 2 2" stroke="#29b5e8" stroke-width="1.5" stroke-linecap="round"/></svg>`;
            }
            if (p.includes('mongodb')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#00ed64"><path d="M8 1c.5 1.5 4 4.5 4 8a4 4 0 0 1-8 0c0-3.5 3.5-6.5 4-8z"/><path d="M8 3v10" stroke="#001e2b" stroke-width="0.8"/></svg>`;
            }
            if (p.includes('salesforce')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#00a1e0"><path d="M6 4a3.5 3.5 0 0 1 3.4 2.7 3 3 0 0 1 3.6 3 2.5 2.5 0 0 1-2.5 2.3H5a3 3 0 0 1-.9-5.8A3.5 3.5 0 0 1 6 4z"/></svg>`;
            }
            if (p.includes('postman')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#ff6c37"><circle cx="8" cy="8" r="6.5"/><path d="M5 8l2.5 2.5L11 5" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
            }
            if (p.includes('juniper')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><rect x="2" y="2" width="12" height="12" rx="3" fill="#00739c"/><path d="M6 6h4v4H6z" fill="#ffffff"/></svg>`;
            }
            if (p.includes('fortinet')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#ee3124"><rect x="2" y="3" width="5.5" height="4.5" rx="1"/><rect x="8.5" y="3" width="5.5" height="4.5" rx="1"/><rect x="2" y="8.5" width="5.5" height="4.5" rx="1"/><rect x="8.5" y="8.5" width="5.5" height="4.5" rx="1"/></svg>`;
            }
            if (p.includes('isc2')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#008752"><path d="M8 1L2.5 3v5c0 3.5 2.5 6 5.5 7 3-1 5.5-3.5 5.5-7V3L8 1zm0 3a2.5 2.5 0 0 1 2.5 2.5c0 1.2-.8 2.2-2 2.4v2.1h-1V8.9a2.5 2.5 0 0 1-2-2.4A2.5 2.5 0 0 1 8 4z"/></svg>`;
            }
            if (p.includes('qualys')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" stroke="#ed1c24" stroke-width="1.5" fill="none"/><path d="M9 10l2.5 2.5" stroke="#ed1c24" stroke-width="2" stroke-linecap="round"/></svg>`;
            }
            if (p.includes('red hat')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16"><path d="M14.5 10.5c-.8 0-1.8-.3-2.6-.7-.6 1.4-2 2.2-3.9 2.2-2.3 0-4-1.2-4-2.8 0-.4.1-.7.3-1C2.9 8.2 2 7.7 2 7.2c0-.5.8-1 2.3-1.3C5 4.5 6.4 3 8 3c2.2 0 3.7 1.6 4.1 3.8 1.4.3 2.4 1 2.4 1.8 0 .5-.7 1-2 1.3.4.2.8.4 1.2.6.5-.2.8-.2.8 0 0 .5-1.1.8-2 .8z" fill="#ee0000"/></svg>`;
            }
            if (p.includes('hashicorp')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#027bfd"><path d="M2.5 2h3v12h-3zm8 0h3v12h-3zm-5.5 4.5h5v3h-5z"/></svg>`;
            }
            if (p.includes('palo alto')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#fa582d"><path d="M8 1L2 4v5c0 3.5 2.5 5.5 6 6 3.5-.5 6-2.5 6-6V4L8 1zm0 2.2l4 2v3.8c0 2.4-1.6 3.9-4 4.3-2.4-.4-4-1.9-4-4.3V5.2l4-2z"/></svg>`;
            }
            if (p.includes('gitlab')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#fc6d26"><path d="M8 14.5L1.5 5.8l2.2-6.5L8 4.2l4.3-4.9 2.2 6.5L8 14.5z"/></svg>`;
            }
            if (p.includes('splunk')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#f15b24"><path d="M3 2.5l5.5 5.5L3 13.5h3l5.5-5.5L6 2.5H3zm7 11h3v-2h-3v2z"/></svg>`;
            }
            if (p.includes('ibm')) {
                return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="#0f62fe"><rect x="1" y="2" width="14" height="1"/><rect x="1" y="4" width="14" height="1"/><rect x="1" y="6" width="14" height="1"/><rect x="1" y="8" width="14" height="1"/><rect x="1" y="10" width="14" height="1"/><rect x="1" y="12" width="14" height="1"/></svg>`;
            }
            return `<svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 16 16" fill="var(--accent-fg)"><circle cx="8" cy="8" r="6"/></svg>`;
        }

        // Canonical 10 Developer Color Palettes
        const THEMES = [
            { id: 'catppuccin-latte', name: 'Catppuccin Latte', dot: '#1e66f5', meta: '#eff1f5', type: 'light' },
            { id: 'catppuccin-mocha', name: 'Catppuccin Mocha', dot: '#cba6f7', meta: '#1e1e2e', type: 'dark' },
            { id: 'github-dark', name: 'GitHub Dark', dot: '#58a6ff', meta: '#0d1117', type: 'dark' },
            { id: 'github-light', name: 'GitHub Light', dot: '#0969da', meta: '#ffffff', type: 'light' },
            { id: 'dracula', name: 'Dracula', dot: '#bd93f9', meta: '#282a36', type: 'dark' },
            { id: 'nord', name: 'Nord', dot: '#88c0d0', meta: '#2e3440', type: 'dark' },
            { id: 'tokyo-night', name: 'Tokyo Night', dot: '#7aa2f7', meta: '#1a1b26', type: 'dark' },
            { id: 'one-dark', name: 'One Dark', dot: '#61afef', meta: '#282c34', type: 'dark' },
            { id: 'gruvbox-dark', name: 'Gruvbox Dark', dot: '#fe8019', meta: '#282828', type: 'dark' },
            { id: 'solarized-light', name: 'Solarized Light', dot: '#2aa198', meta: '#fdf6e3', type: 'light' }
        ];

        function selectTheme(id) {
            applyTheme(id);
            closeThemeDropdown();
            toast('Theme: ' + getThemeName(id));
        }

        function getThemeName(id) {
            const t = THEMES.find(x => x.id === id);
            return t ? t.name : id;
        }

        function applyTheme(id) {
            let targetId = id;
            if (id === 'dark') targetId = 'github-dark';
            if (id === 'light') targetId = 'catppuccin-latte';

            const theme = THEMES.find(t => t.id === targetId) || THEMES[0];
            document.documentElement.setAttribute('data-theme', theme.id);
            localStorage.setItem('certpulse_theme_v2', theme.id);
            localStorage.setItem('theme', theme.id);
            
            const meta = document.getElementById('themeColorMeta');
            if (meta) meta.content = theme.meta;

            // Sync Sun/Moon icon for quick toggle button
            const isLight = (theme.type === 'light');
            const sun = document.getElementById('themeIconSun');
            const moon = document.getElementById('themeIconMoon');
            if (sun && moon) {
                if (isLight) {
                    sun.classList.remove('hidden');
                    moon.classList.add('hidden');
                } else {
                    sun.classList.add('hidden');
                    moon.classList.remove('hidden');
                }
            }
        }

        const switchTheme = applyTheme;

        function toggleTheme() {
            const current = document.documentElement.getAttribute('data-theme') || 'catppuccin-latte';
            const currentTheme = THEMES.find(t => t.id === current);
            const isCurrentLight = currentTheme ? (currentTheme.type === 'light') : (current.includes('light') || current.includes('latte'));
            const nextTheme = isCurrentLight ? 'github-dark' : 'catppuccin-latte';
            applyTheme(nextTheme);
            toast('Theme: ' + getThemeName(nextTheme));
        }

        function toggleThemeDropdown() {
            const menu = document.getElementById('themeDropdownMenu');
            if (menu) {
                menu.classList.toggle('hidden');
            }
        }

        function closeThemeDropdown() {
            const menu = document.getElementById('themeDropdownMenu');
            if (menu) {
                menu.classList.add('hidden');
            }
        }

        // Global Synchronized 4-Timezone World Telemetry (UTC, IST, EDT/EST, CEST/CET)
        function updateWorldClock() {
            let syncDate;
            try {
                syncDate = new Date(LAST_SYNC_ISO);
                if (!Number.isFinite(syncDate.getTime())) {
                    syncDate = new Date();
                }
            } catch (e) {
                syncDate = new Date();
            }
            const utcTime = syncDate.toLocaleString('en-US', { timeZone: 'UTC', hour12: false, hour: '2-digit', minute: '2-digit' }) + ' UTC';
            const istTime = syncDate.toLocaleString('en-US', { timeZone: 'Asia/Kolkata', hour12: false, hour: '2-digit', minute: '2-digit' }) + ' IST';
            const etTime = syncDate.toLocaleString('en-US', { timeZone: 'America/New_York', hour12: false, hour: '2-digit', minute: '2-digit' }) + ' EDT';
            const cetTime = syncDate.toLocaleString('en-US', { timeZone: 'Europe/Berlin', hour12: false, hour: '2-digit', minute: '2-digit' }) + ' CEST';

            const navTimeText = document.getElementById('navTimezoneText');
            if (navTimeText) navTimeText.textContent = `Last Synced: ${utcTime} • ${istTime} • ${etTime} • ${cetTime}`;

            const heroUtc = document.getElementById('heroCadenceUtc');
            if (heroUtc) heroUtc.textContent = utcTime;
            const heroIst = document.getElementById('heroCadenceIst');
            if (heroIst) heroIst.textContent = istTime;
            const heroEt = document.getElementById('heroCadenceEt');
            if (heroEt) heroEt.textContent = etTime;
            const heroCet = document.getElementById('heroCadenceCet');
            if (heroCet) heroCet.textContent = cetTime;
        }

        // Backwards compatibility stubs
        function toggleOfferChecked() {}
        function clearAllChecked() {}
        function updateGoalCounters() { updateWorldClock(); }

        // Tab Switching Engine (Vouchers vs Tech Radar vs Where Offers Are Applied)
        function switchMainTab(tab, updateUrl = true) {
            currentMainTab = tab;
            const vouchersSec = document.getElementById('vouchersSection');
            const newsSec = document.getElementById('newsSection');
            const redemptionSec = document.getElementById('redemptionSection');
            const tabVouchers = document.getElementById('tabBtnVouchers');
            const tabNews = document.getElementById('tabBtnNews');
            const tabRedemption = document.getElementById('tabBtnRedemption');

            if (tab === 'vouchers') {
                if (vouchersSec) vouchersSec.classList.remove('hidden');
                if (newsSec) newsSec.classList.add('hidden');
                if (redemptionSec) redemptionSec.classList.add('hidden');
                if (tabVouchers) {
                    tabVouchers.style.borderColor = 'var(--accent-fg)';
                    tabVouchers.style.color = 'var(--fg-default)';
                }
                if (tabNews) {
                    tabNews.style.borderColor = 'transparent';
                    tabNews.style.color = 'var(--fg-muted)';
                }
                if (tabRedemption) {
                    tabRedemption.style.borderColor = 'transparent';
                    tabRedemption.style.color = 'var(--fg-muted)';
                }
            } else if (tab === 'news') {
                if (vouchersSec) vouchersSec.classList.add('hidden');
                if (newsSec) newsSec.classList.remove('hidden');
                if (redemptionSec) redemptionSec.classList.add('hidden');
                if (tabNews) {
                    tabNews.style.borderColor = 'var(--accent-fg)';
                    tabNews.style.color = 'var(--fg-default)';
                }
                if (tabVouchers) {
                    tabVouchers.style.borderColor = 'transparent';
                    tabVouchers.style.color = 'var(--fg-muted)';
                }
                if (tabRedemption) {
                    tabRedemption.style.borderColor = 'transparent';
                    tabRedemption.style.color = 'var(--fg-muted)';
                }
                renderNews();
            } else if (tab === 'redemption') {
                if (vouchersSec) vouchersSec.classList.add('hidden');
                if (newsSec) newsSec.classList.add('hidden');
                if (redemptionSec) redemptionSec.classList.remove('hidden');
                if (tabRedemption) {
                    tabRedemption.style.borderColor = 'var(--accent-fg)';
                    tabRedemption.style.color = 'var(--fg-default)';
                }
                if (tabVouchers) {
                    tabVouchers.style.borderColor = 'transparent';
                    tabVouchers.style.color = 'var(--fg-muted)';
                }
                if (tabNews) {
                    tabNews.style.borderColor = 'transparent';
                    tabNews.style.color = 'var(--fg-muted)';
                }
                renderRedemption();
            }

            if (updateUrl) {
                const url = new URL(window.location);
                if (tab === 'news') url.searchParams.set('tab', 'news');
                else if (tab === 'redemption') url.searchParams.set('tab', 'redemption');
                else url.searchParams.delete('tab');
                window.history.replaceState({}, '', url);
            }
        }

        // Layout View Switching Engine (Grid, Table, Timeline, Matrix)
        function setLayoutView(view, updateUrl = true) {
            currentLayout = view;
            const containers = {
                grid: document.getElementById('cardsViewContainer'),
                list: document.getElementById('listViewContainer'),
                timeline: document.getElementById('timelineViewContainer'),
                matrix: document.getElementById('matrixViewContainer')
            };
            const buttons = {
                grid: document.getElementById('viewBtnGrid'),
                list: document.getElementById('viewBtnList'),
                timeline: document.getElementById('viewBtnTimeline'),
                matrix: document.getElementById('viewBtnMatrix')
            };

            const validViews = ['grid', 'list', 'timeline', 'matrix'];
            validViews.forEach(v => {
                if (containers[v]) {
                    if (v === view) containers[v].classList.remove('hidden');
                    else containers[v].classList.add('hidden');
                }
                if (buttons[v]) {
                    if (v === view) {
                        buttons[v].style.backgroundColor = 'var(--btn-default-bg)';
                        buttons[v].style.color = 'var(--fg-default)';
                        buttons[v].classList.add('font-semibold');
                    } else {
                        buttons[v].style.backgroundColor = 'transparent';
                        buttons[v].style.color = 'var(--fg-muted)';
                        buttons[v].classList.remove('font-semibold');
                    }
                }
            });

            renderCards();

            if (updateUrl) {
                const url = new URL(window.location);
                if (view !== 'grid') url.searchParams.set('view', view);
                else url.searchParams.delete('view');
                window.history.replaceState({}, '', url);
            }
        }

        function cycleLayoutView() {
            const views = ['grid', 'list', 'timeline', 'matrix'];
            const nextIdx = (views.indexOf(currentLayout) + 1) % views.length;
            setLayoutView(views[nextIdx]);
            toast('View: ' + views[nextIdx].toUpperCase());
        }

        // Filtering & Rendering Engine
        function filterCategory(cat) {
            currentCategory = cat;
            document.querySelectorAll('#filterPills button').forEach(btn => {
                if (btn.getAttribute('data-cat') === cat) {
                    btn.style.backgroundColor = 'var(--accent-emphasis)';
                    btn.style.color = '#ffffff';
                } else {
                    btn.style.backgroundColor = 'var(--canvas-default)';
                    btn.style.color = 'var(--fg-muted)';
                }
            });
            renderCards();
        }

        function onStatusFilterChange() {
            renderCards();
        }

        function clearSearch() {
            const input = document.getElementById('searchInput');
            if (input) {
                input.value = '';
                currentSearch = '';
                input.focus();
            }
            const clearBtn = document.getElementById('clearSearchBtn');
            if (clearBtn) clearBtn.classList.add('hidden');
            const badge = document.getElementById('searchMatchesBadge');
            if (badge) badge.classList.add('hidden');
            renderCards();
        }

        function getFilteredOffers() {
            const statusEl = document.getElementById('statusFilter');
            const statusVal = statusEl ? statusEl.value : 'active';
            const sortEl = document.getElementById('sortSelect');
            const sortVal = sortEl ? sortEl.value : 'val-desc';
            
            return offersData.filter(o => {
                // Credential Tier Segmentation Filter
                if (currentTier === 'proctored_exam') {
                    const isProctored = o.credential_tier === 'proctored_exam' || o.credential_tier === 'primary';
                    if (!isProctored) return false;
                } else if (currentTier === 'skill_badge_lab') {
                    const isBadge = o.credential_tier === 'skill_badge_lab' || o.credential_tier === 'secondary';
                    if (!isBadge) return false;
                }

                if (currentCategory === 'History') {
                    if (!o.is_historical_archive && o.status !== 'Expired') return false;
                } else if (currentCategory !== 'All') {
                    const cat = (o.category || '').toLowerCase();
                    const platform = (o.platform || '').toLowerCase();
                    if (currentCategory === 'Cloud' && !cat.includes('cloud') && !platform.includes('cloud')) return false;
                    if (currentCategory === 'Security' && !cat.includes('security')) return false;
                    if (currentCategory === 'DevOps' && !cat.includes('devops')) return false;
                    if (currentCategory === 'AI & Data' && !cat.includes('ai') && !cat.includes('data')) return false;
                    if (currentCategory === 'Networking' && !cat.includes('network')) return false;
                }

                if (statusVal === 'active' && o.status !== 'Active') return false;
                if (statusVal === 'closed' && (o.status === 'Active' || o.is_historical_archive)) return false;
                if (statusVal === 'history' && !o.is_historical_archive) return false;

                if (currentSearch) {
                    const query = currentSearch.toLowerCase();
                    const tierTerm = (o.credential_tier === 'proctored_exam' || o.credential_tier === 'primary')
                        ? 'proctored exam written primary'
                        : 'skill badge lab secondary unproctored';
                    const text = [
                        o.title, o.platform, o.certification_name, o.category,
                        o.exam_code, o.difficulty_tier, o.eligibility, tierTerm,
                        o.credential_tier, o.voucher_code
                    ].filter(Boolean).join(' ').toLowerCase();
                    if (!text.includes(query)) return false;
                }

                return true;
            }).sort((a, b) => {
                if (sortVal === 'val-desc') return (b.value_usd || 0) - (a.value_usd || 0);
                if (sortVal === 'val-asc') return (a.value_usd || 0) - (b.value_usd || 0);
                if (sortVal === 'name-asc') return (a.platform || '').localeCompare(b.platform || '');
                return 0;
            });
        }

        function renderCards() {
            const filtered = getFilteredOffers();
            const countEl = document.getElementById('resultsCount');
            if (countEl) countEl.textContent = 'Showing ' + filtered.length + ' of ' + offersData.length + ' vouchers';

            if (currentLayout === 'grid') renderGridView(filtered);
            else if (currentLayout === 'list') renderTableView(filtered);
            else if (currentLayout === 'timeline') renderTimelineView(filtered);
            else if (currentLayout === 'matrix') renderMatrixView(filtered);
        }

        function renderGridView(filtered) {
            const renderCardHtml = (o) => {
                const valText = o.value_usd ? '$' + o.value_usd + ' USD' : '100% Free';
                const statusBadge = o.status === 'Active' 
                    ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold" style="background-color: var(--success-subtle); color: var(--success-fg);">🟢 Active</span>'
                    : '<span class="px-2 py-0.5 rounded text-[10px] font-bold" style="background-color: var(--attention-subtle); color: var(--attention-fg);">' + o.status + '</span>';

                const isProctored = o.credential_tier === 'proctored_exam' || o.credential_tier === 'primary';
                const credBadge = isProctored 
                    ? '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold border" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);">🎓 Written Proctored Exam</span>' 
                    : '<span class="px-1.5 py-0.5 rounded text-[10px] font-medium border" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">🎖️ Skill Badge & Lab</span>';

                const tierBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-medium border" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">' + (o.difficulty_tier || 'Foundational') + '</span>';

                const tv = o.truth_verification;
                let truthBadge = '';
                if (tv) {
                    if (tv.policy_type === 'partial_discount_copay') {
                        truthBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold border border-amber-500/40 bg-amber-500/10 text-amber-500" title="Official 75% Discount - Pearson VUE Copay Required">⚠️ 75% Off ($50 Fee)</span>';
                    } else if (tv.policy_type === 'student_verified_only') {
                        truthBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-medium border border-blue-500/40 bg-blue-500/10 text-blue-400" title="Verified Students Only (GitHub Student Pack)">🎓 Student Pack</span>';
                    } else if (tv.policy_type === 'annual_window_closed') {
                        truthBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-medium border border-amber-500/40 bg-amber-500/10 text-amber-500" title="Annual Window Closed - Reopens April 2027">📅 Annual Window Closed</span>';
                    } else if (tv.policy_type === 'verified_100pct_free') {
                        truthBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-bold border border-emerald-500/40 bg-emerald-500/10 text-emerald-500" title="100% Free Verified Proctored Exam ($0.00)">✓ $0.00 Verified</span>';
                    }
                }

                const zeroConfirmedBadge = o.last_zero_dollar_confirmed_date 
                    ? '<span class="px-1.5 py-0.5 rounded text-[10px] font-medium border" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);" title="Last confirmed 100% free with zero dollar terms">✓ $0: ' + o.last_zero_dollar_confirmed_date + '</span>' 
                    : '';

                return `
                <div class="primer-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between gap-3 relative transition-all" id="card-${o.id}">
                    <div>
                        <div class="flex items-center justify-between gap-2 mb-2">
                            <div class="flex items-center gap-2 min-w-0">
                                ${getPlatformIconSvg(o.platform)}
                                <span class="font-bold text-xs truncate" style="color: var(--fg-default);">${o.platform}</span>
                            </div>
                            <div class="flex items-center gap-1.5 flex-shrink-0">
                                ${statusBadge}
                            </div>
                        </div>

                        <div class="mb-1.5">
                            ${credBadge}
                        </div>

                        <h3 class="font-bold text-sm sm:text-base leading-snug tracking-tight mt-1" style="color: var(--fg-default);">${o.title}</h3>
                        <div class="flex items-center gap-2 mt-2 flex-wrap">
                            ${tierBadge}
                            ${zeroConfirmedBadge}
                            <span class="text-[11px] font-bold tabular-nums" style="color: var(--success-fg);">${valText}</span>
                            ${truthBadge}
                            <button onclick="openProofModal('${o.id}')" class="text-[10px] px-1.5 py-0.5 rounded font-medium border hover:opacity-80 transition cursor-pointer inline-flex items-center gap-1" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);" title="View Verified Zero-Dollar Proof Lightbox">
                                <span>🛡️ ${o.authenticity_score || 100}% Proof</span>
                            </button>
                        </div>

                        <p class="text-xs mt-2.5 leading-relaxed text-pretty" style="color: var(--fg-muted);">${o.eligibility || 'Open to all developers & engineers globally.'}</p>
                    </div>

                    <div class="pt-3 border-t flex items-center justify-between gap-2 flex-wrap" style="border-color: var(--border-muted);">
                        <div class="flex items-center gap-1.5 flex-wrap">
                            <button onclick="copySteps('${o.id}')" class="text-xs font-semibold px-2.5 py-1.5 rounded-lg border hover:opacity-80 transition cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                                Copy Guide
                            </button>
                            <button onclick="openRedemptionFor('${o.id}')" class="text-xs font-semibold px-2.5 py-1.5 rounded-lg border hover:opacity-80 transition cursor-pointer" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);" title="Where & How Offer is Applied ($0.00)">
                                $0.00 Apply
                            </button>
                            <button onclick="openProofModal('${o.id}')" class="text-xs font-semibold px-2.5 py-1.5 rounded-lg border hover:opacity-80 transition cursor-pointer inline-flex items-center gap-1" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);" title="View Verified Zero-Dollar Proof Lightbox">
                                <span>📸 Proof</span>
                            </button>
                        </div>
                        <a href="${o.direct_verified_url || o.verified_vendor_url || o.url}" target="_blank" rel="noopener" class="text-xs font-semibold px-3 py-1.5 rounded-lg text-white transition active:scale-[0.98] inline-flex items-center gap-1 cursor-pointer" style="background-color: var(--btn-primary-bg);">
                            <span>Claim Free</span>
                            <span>→</span>
                        </a>
                    </div>
                </div>`;
            };

            const grid = document.getElementById('offersGrid');
            if (!grid) return;
            if (filtered.length === 0) {
                grid.innerHTML = '<div class="col-span-full p-8 text-center rounded-xl border" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">No certifications match your active search or filters.</div>';
                return;
            }

            if (currentTier !== 'all') {
                grid.innerHTML = filtered.map(o => renderCardHtml(o)).join('');
                return;
            }

            const proctoredList = filtered.filter(o => o.credential_tier === 'proctored_exam' || o.credential_tier === 'primary');
            const badgesList = filtered.filter(o => o.credential_tier === 'skill_badge_lab' || o.credential_tier === 'secondary');

            let html = '';

            // 1. Primary Tier: Written Proctored Exams & Discounts (Top Section)
            if (proctoredList.length > 0) {
                html += `
                <div class="col-span-full flex items-center justify-between p-3 rounded-xl border" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                    <div class="flex items-center gap-2">
                        <span class="text-base">🎓</span>
                        <div>
                            <h2 class="font-bold text-xs sm:text-sm tracking-tight" style="color: var(--fg-default);">Primary Tier: Industry-Recognized Written Proctored Exams & Discounts</h2>
                            <p class="text-[11px]" style="color: var(--fg-muted);">Pearson VUE / Kryterion / Webassessor proctored exams, official waivers, and verified voucher waves (${proctoredList.length} Opportunities)</p>
                        </div>
                    </div>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold border" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);">${proctoredList.length} Exams</span>
                </div>`;
                html += proctoredList.map(o => renderCardHtml(o)).join('');
            }

            // 2. Secondary Tier: Digital Skill Badges & Cloud Labs (Secondary Collapsible Section)
            if (badgesList.length > 0) {
                html += `
                <details class="col-span-full mt-4 rounded-2xl border p-4 sm:p-5 transition-all shadow-xs group" style="background-color: var(--canvas-subtle); border-color: var(--border-default);" open>
                    <summary class="cursor-pointer list-none flex items-center justify-between select-none">
                        <div class="flex items-center gap-2.5">
                            <span class="text-base">🎖️</span>
                            <div>
                                <div class="flex items-center gap-2">
                                    <h2 class="font-bold text-xs sm:text-sm tracking-tight" style="color: var(--fg-default);">Secondary Tier: Free Digital Skill Badges & Hands-On Cloud Labs</h2>
                                    <span class="px-2 py-0.5 rounded text-[10px] font-semibold border" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">${badgesList.length} Badges</span>
                                </div>
                                <p class="text-[11px] mt-0.5" style="color: var(--fg-muted);">Unproctored practical learning paths, sandbox labs, and verifiable Credly/Skill badges (Click to collapse / expand)</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-lg border transition group-open:rotate-180" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                            <svg class="w-3.5 h-3.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                        </div>
                    </summary>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-4 mt-4 border-t" style="border-color: var(--border-muted);">
                        ${badgesList.map(o => renderCardHtml(o)).join('')}
                    </div>
                </details>`;
            }

            grid.innerHTML = html;
        }

        function renderTableView(filtered) {
            const tbody = document.getElementById('offersTableBody');
            if (!tbody) return;
            if (filtered.length === 0) {
                tbody.innerHTML = '<div class="p-8 text-center text-xs" style="color: var(--fg-muted);">No records found matching criteria.</div>';
                return;
            }

            const renderTableRow = (o) => {
                const valText = o.value_usd ? '$' + o.value_usd : 'Free';
                const isProctored = o.credential_tier === 'proctored_exam' || o.credential_tier === 'primary';
                const credBadge = isProctored 
                    ? '<span class="text-[10px] font-bold px-1.5 py-0.5 rounded border" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);">🎓 Exam</span>' 
                    : '<span class="text-[10px] px-1.5 py-0.5 rounded border" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">🎖️ Badge</span>';

                const tv = o.truth_verification;
                let truthBadge = '';
                if (tv) {
                    if (tv.policy_type === 'partial_discount_copay') {
                        truthBadge = '<span class="text-[10px] font-bold text-amber-500 ml-1.5" title="75% Discount - Pearson VUE Copay">⚠️ 75% Off</span>';
                    } else if (tv.policy_type === 'student_verified_only') {
                        truthBadge = '<span class="text-[10px] text-blue-400 ml-1.5" title="Student Pack">🎓 Student</span>';
                    } else if (tv.policy_type === 'annual_window_closed') {
                        truthBadge = '<span class="text-[10px] text-amber-500 ml-1.5" title="Annual Window Closed">📅 Closed</span>';
                    }
                }

                return `
                <div class="p-3 sm:px-4 sm:py-3.5 grid grid-cols-1 sm:grid-cols-12 gap-2 sm:gap-3 items-center hover:bg-slate-500/5 transition">
                    <div class="sm:col-span-3 flex items-center gap-2 min-w-0">
                        ${getPlatformIconSvg(o.platform)}
                        <div class="flex flex-col min-w-0">
                            <span class="font-bold text-xs truncate" style="color: var(--fg-default);">${o.platform}</span>
                            <div class="flex items-center gap-1 mt-0.5">${credBadge} ${truthBadge}</div>
                        </div>
                    </div>
                    <div class="sm:col-span-5 min-w-0">
                        <div class="font-semibold text-xs sm:text-sm truncate" style="color: var(--fg-default);">${o.certification_name || o.title}</div>
                        <div class="text-[11px]" style="color: var(--fg-muted);">${o.category} • ${o.difficulty_tier || 'Foundational'}</div>
                    </div>
                    <div class="sm:col-span-1 sm:text-center text-xs font-bold tabular-nums" style="color: var(--success-fg);">${valText}</div>
                    <div class="sm:col-span-3 flex items-center sm:justify-end gap-1.5 flex-wrap">
                        <button onclick="openProofModal('${o.id}')" class="text-[11px] font-semibold px-2 py-1 rounded border cursor-pointer inline-flex items-center gap-1" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);" title="View Verified Zero-Dollar Proof Lightbox">📸 Proof</button>
                        <button onclick="openRedemptionFor('${o.id}')" class="text-[11px] font-semibold px-2 py-1 rounded border cursor-pointer" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);" title="Where Offer is Applied ($0.00)">$0.00</button>
                        <a href="${o.direct_verified_url || o.verified_vendor_url || o.url}" target="_blank" class="text-xs font-semibold px-2.5 py-1 rounded text-white" style="background-color: var(--btn-primary-bg);">Claim →</a>
                    </div>
                </div>`;
            };

            if (currentTier !== 'all') {
                tbody.innerHTML = filtered.map(renderTableRow).join('');
                return;
            }

            const proctored = filtered.filter(o => o.credential_tier === 'proctored_exam' || o.credential_tier === 'primary');
            const badges = filtered.filter(o => o.credential_tier === 'skill_badge_lab' || o.credential_tier === 'secondary');

            let html = '';
            if (proctored.length > 0) {
                html += `<div class="px-4 py-2 text-xs font-bold flex items-center gap-2 border-b" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-default);"><span>🎓 Primary: Written Proctored Exams & Discounts (${proctored.length})</span></div>`;
                html += proctored.map(renderTableRow).join('');
            }
            if (badges.length > 0) {
                html += `<div class="px-4 py-2 text-xs font-bold flex items-center gap-2 border-b mt-2" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);"><span>🎖️ Secondary: Free Digital Skill Badges & Cloud Labs (${badges.length})</span></div>`;
                html += badges.map(renderTableRow).join('');
            }
            tbody.innerHTML = html;
        }

        function renderTimelineView(filtered) {
            const container = document.getElementById('offersTimeline');
            if (!container) return;
            container.innerHTML = `
            <div class="p-4 rounded-xl border mb-4" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                <h3 class="font-bold text-sm" style="color: var(--fg-default);">Recurrence & Promotional Timeline Roadmap</h3>
                <p class="text-xs mt-1" style="color: var(--fg-muted);">Tracks seasonal promotional waves, annual developer conferences, and recurring voucher cycles.</p>
            </div>
            <div class="space-y-4">
                ${filtered.map(o => `
                <div class="primer-card rounded-xl p-4 border flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div class="flex items-start gap-3">
                        ${getPlatformIconSvg(o.platform)}
                        <div>
                            <div class="font-bold text-sm" style="color: var(--fg-default);">${o.platform} — ${o.title}</div>
                            <div class="text-xs mt-1" style="color: var(--fg-muted);">Cadence: <span class="font-semibold text-blue-500">${o.recurrence_pattern || 'Annual Conference Cycle'}</span> • Period: ${o.time_period || 'Continuous'}</div>
                        </div>
                    </div>
                    <div class="flex items-center gap-2 flex-shrink-0">
                        <button onclick="openProofModal('${o.id}')" class="px-2.5 py-1 rounded text-xs border font-medium cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);" title="View Verified Zero-Dollar Proof Lightbox">
                            📸 Proof
                        </button>
                        <a href="${o.direct_verified_url || o.verified_vendor_url || o.url}" target="_blank" class="px-3 py-1 rounded text-xs font-semibold text-white" style="background-color: var(--btn-primary-bg);">Open →</a>
                    </div>
                </div>`).join('')}
            </div>`;
        }

        function renderMatrixView(filtered) {
            const container = document.getElementById('offersMatrix');
            if (!container) return;
            const domains = [
                { id: 'cloud', label: 'Cloud Computing', filter: ['cloud', 'crm'] },
                { id: 'security', label: 'Cybersecurity & Defense', filter: ['security'] },
                { id: 'ai_data', label: 'AI, Data & Analytics', filter: ['ai', 'data'] },
                { id: 'devops', label: 'DevOps & Cloud Native', filter: ['devops', 'api', 'native'] },
                { id: 'networking', label: 'Networking & Systems', filter: ['network'] }
            ];

            container.innerHTML = domains.map(d => {
                const inDomain = filtered.filter(o => {
                    const cat = (o.category || '').toLowerCase();
                    return d.filter.some(k => cat.includes(k));
                });

                return `
                <div class="rounded-xl border p-4" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                    <div class="flex items-center justify-between border-b pb-2 mb-3" style="border-color: var(--border-muted);">
                        <h4 class="font-bold text-sm" style="color: var(--fg-default);">${d.label}</h4>
                        <span class="text-xs font-bold tabular-nums" style="color: var(--accent-fg);">${inDomain.length} Offers</span>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        ${inDomain.length === 0 ? '<div class="text-xs p-3" style="color: var(--fg-muted);">No active offers in this domain.</div>' : inDomain.map(o => `
                        <div class="primer-card p-3 rounded-lg border text-xs flex flex-col justify-between gap-2">
                            <div>
                                <div class="flex items-center justify-between gap-1 mb-1">
                                    <span class="font-bold truncate" style="color: var(--fg-default);">${o.platform}</span>
                                    <span class="font-bold text-emerald-500">${o.value_usd ? '$' + o.value_usd : 'Free'}</span>
                                </div>
                                <div class="font-medium text-slate-700 dark:text-slate-300 truncate">${o.certification_name || o.title}</div>
                            </div>
                            <div class="flex items-center justify-between pt-2 border-t" style="border-color: var(--border-muted);">
                                <span class="text-[10px] font-mono">${o.difficulty_tier || 'Foundational'}</span>
                                <div class="flex items-center gap-2">
                                    <button onclick="openProofModal('${o.id}')" class="text-[11px] font-medium hover:underline cursor-pointer inline-flex items-center gap-0.5" title="View Verified Zero-Dollar Proof Lightbox">📸 Proof</button>
                                    <a href="${o.direct_verified_url || o.verified_vendor_url || o.url}" target="_blank" class="text-blue-500 font-semibold hover:underline">Claim →</a>
                                </div>
                            </div>
                        </div>`).join('')}
                    </div>
                </div>`;
            }).join('');
        }

        // Copy Claiming Instructions to Clipboard
        function copySteps(id) {
            const offer = offersData.find(o => o.id === id);
            if (!offer) return;
            const steps = [
                'Free Certification Opportunity: ' + offer.title,
                'Provider: ' + offer.platform,
                'Value: $' + (offer.value_usd || 0) + ' USD',
                'Eligibility: ' + offer.eligibility,
                'Steps to Claim: ' + offer.claim_steps,
                'Official URL: ' + offer.url
            ].join('\\n');

            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(steps).then(() => {
                    toast('Claiming guide copied to clipboard!');
                }).catch(() => {
                    prompt('Copy Claiming Instructions:', steps);
                });
            } else {
                prompt('Copy Claiming Instructions:', steps);
            }
        }

        // Export Filtered JSON
        function exportFilteredJson() {
            const filtered = getFilteredOffers();
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(filtered, null, 2));
            const dlAnchor = document.createElement('a');
            dlAnchor.setAttribute("href", dataStr);
            dlAnchor.setAttribute("download", "certpulse_filtered_vouchers.json");
            document.body.appendChild(dlAnchor);
            dlAnchor.click();
            dlAnchor.remove();
            toast('Exported ' + filtered.length + ' vouchers as JSON');
        }

        // Search Input Handlers
        function setupSearchListener() {
            const searchInput = document.getElementById('searchInput');
            if (!searchInput) return;
            searchInput.addEventListener('input', function(e) {
                currentSearch = e.target.value.trim();
                const clearBtn = document.getElementById('clearSearchBtn');
                const matchesBadge = document.getElementById('searchMatchesBadge');
                
                if (currentSearch) {
                    if (clearBtn) clearBtn.classList.remove('hidden');
                    const count = getFilteredOffers().length;
                    if (matchesBadge) {
                        matchesBadge.textContent = count + ' found';
                        matchesBadge.classList.remove('hidden');
                    }
                } else {
                    if (clearBtn) clearBtn.classList.add('hidden');
                    if (matchesBadge) matchesBadge.classList.add('hidden');
                }
                renderCards();
            });
        }

        // Keyboard Shortcut Engine
        document.addEventListener('keydown', function(e) {
            const proofModal = document.getElementById('proofModal');
            if (proofModal && !proofModal.classList.contains('hidden')) {
                if (e.key === 'Escape') {
                    e.preventDefault();
                    closeProofModal();
                    return;
                }
                if (e.key === 'Tab') {
                    const focusables = proofModal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
                    if (focusables.length > 0) {
                        const firstEl = focusables[0];
                        const lastEl = focusables[focusables.length - 1];
                        if (e.shiftKey) {
                            if (document.activeElement === firstEl) {
                                e.preventDefault();
                                lastEl.focus();
                            }
                        } else {
                            if (document.activeElement === lastEl) {
                                e.preventDefault();
                                firstEl.focus();
                            }
                        }
                    }
                    return;
                }
            }

            if (e.key === 'Escape') {
                closeThemeDropdown();
            }

            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') {
                if (e.key === 'Escape') {
                    e.target.blur();
                    if (e.target.id === 'redemptionSearchInput') {
                        e.target.value = '';
                        renderRedemption();
                    } else if (e.target.id === 'newsSearchInput') {
                        clearNewsSearch();
                    } else {
                        clearSearch();
                    }
                }
                return;
            }

            const key = e.key.toLowerCase();
            if (key === 'v') {
                e.preventDefault();
                cycleLayoutView();
            } else if (key === '1') {
                e.preventDefault();
                switchMainTab('vouchers');
            } else if (key === '2') {
                e.preventDefault();
                switchMainTab('news');
            } else if (key === '3') {
                e.preventDefault();
                switchMainTab('redemption');
            } else if (key === 't' || key === '\\\\') {
                e.preventDefault();
                toggleTheme();
            } else if (key === '/') {
                e.preventDefault();
                if (currentMainTab === 'redemption') {
                    const el = document.getElementById('redemptionSearchInput');
                    if (el) el.focus();
                } else if (currentMainTab === 'news') {
                    const el = document.getElementById('newsSearchInput');
                    if (el) el.focus();
                } else {
                    const el = document.getElementById('searchInput');
                    if (el) el.focus();
                }
            }
        });

        // Close theme dropdown when clicking outside
        document.addEventListener('click', function(e) {
            const dropdown = document.getElementById('themeDropdownMenu');
            const toggle = document.getElementById('themeDropdownToggleBtn');
            if (dropdown && !dropdown.classList.contains('hidden')) {
                if (!dropdown.contains(e.target) && (!toggle || !toggle.contains(e.target))) {
                    dropdown.classList.add('hidden');
                }
            }
        });

        // Toast Engine
        let toastTimer;
        function toast(msg) {
            const el = document.getElementById('toastNotification');
            const msgEl = document.getElementById('toastMessage');
            if (el && msgEl) {
                msgEl.textContent = msg;
                el.classList.remove('translate-y-20', 'opacity-0');
                el.classList.add('translate-y-0', 'opacity-100');
                clearTimeout(toastTimer);
                toastTimer = setTimeout(() => {
                    el.classList.remove('translate-y-0', 'opacity-100');
                    el.classList.add('translate-y-20', 'opacity-0');
                }, 2200);
            }
        }

        function scrollToTop() {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        // News Tab Functionality
        function filterNewsCategory(cat) {
            currentNewsCategory = cat;
            document.querySelectorAll('#newsCategoryPills button').forEach(b => {
                if (b.getAttribute('data-cat') === cat) {
                    b.style.backgroundColor = 'var(--accent-emphasis)';
                    b.style.color = '#ffffff';
                } else {
                    b.style.backgroundColor = 'var(--canvas-default)';
                    b.style.color = 'var(--fg-muted)';
                }
            });
            renderNews();
        }

        function clearNewsSearch() {
            const input = document.getElementById('newsSearchInput');
            if (input) input.value = '';
            currentNewsSearch = '';
            const clearBtn = document.getElementById('clearNewsSearchBtn');
            if (clearBtn) clearBtn.classList.add('hidden');
            const badge = document.getElementById('newsSearchMatchesBadge');
            if (badge) badge.classList.add('hidden');
            renderNews();
        }

        function renderNews() {
            const compEl = document.getElementById('newsCompanySelect');
            const company = compEl ? compEl.value : 'All';
            const sortEl = document.getElementById('newsSortSelect');
            const sort = sortEl ? sortEl.value : 'date-desc';
            const grid = document.getElementById('newsGrid');
            if (!grid) return;

            const filtered = newsData.filter(item => {
                if (currentNewsCategory !== 'All' && item.category !== currentNewsCategory) return false;
                if (company !== 'All' && item.company !== company) return false;
                if (currentNewsSearch) {
                    const q = currentNewsSearch.toLowerCase();
                    const text = (item.title + ' ' + item.summary + ' ' + item.company).toLowerCase();
                    if (!text.includes(q)) return false;
                }
                return true;
            }).sort((a, b) => {
                if (sort === 'date-desc') return (b.published_date || '').localeCompare(a.published_date || '');
                if (sort === 'date-asc') return (a.published_date || '').localeCompare(b.published_date || '');
                if (sort === 'company-asc') return (a.company || '').localeCompare(b.company || '');
                return 0;
            });

            const countEl = document.getElementById('newsResultsCount');
            if (countEl) countEl.textContent = 'Showing ' + filtered.length + ' of ' + newsData.length + ' verified dispatches';

            grid.innerHTML = filtered.map(item => `
            <div class="primer-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between gap-3">
                <div>
                    <div class="flex items-center justify-between text-xs mb-2">
                        <span class="font-bold" style="color: var(--accent-fg);">${item.company}</span>
                        <span class="text-[10px] font-mono tabular-nums" style="color: var(--fg-subtle);">${item.published_date}</span>
                    </div>
                    <h4 class="font-bold text-sm sm:text-base leading-snug tracking-tight" style="color: var(--fg-default);">${item.title}</h4>
                    <p class="text-xs mt-2 leading-relaxed text-pretty" style="color: var(--fg-muted);">${item.summary}</p>
                </div>
                <div class="pt-3 border-t flex items-center justify-between text-xs" style="border-color: var(--border-muted);">
                    <span class="text-[10px] font-mono truncate max-w-[150px]" style="color: var(--fg-subtle);">${item.source_domain}</span>
                    <a href="${item.url}" target="_blank" rel="noopener" class="font-semibold text-blue-500 hover:underline inline-flex items-center gap-1">
                        <span>Read Dispatch</span>
                        <span>→</span>
                    </a>
                </div>
            </div>`).join('');
        }

        // Where Offers Are Applied & Zero-Dollar Checkout Guide Engine
        function copyVoucherToken(token) {
            if (!token) return;
            const fallbackCopy = () => {
                try {
                    const ta = document.createElement('textarea');
                    ta.value = token;
                    ta.style.position = 'fixed';
                    ta.style.opacity = '0';
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand('copy');
                    document.body.removeChild(ta);
                    toast('Copied token: ' + token);
                } catch (e) {
                    toast('Voucher code: ' + token);
                }
            };
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(token).then(() => {
                    toast('Copied token: ' + token);
                }).catch(fallbackCopy);
            } else {
                fallbackCopy();
            }
        }

        function openRedemptionFor(offerId) {
            switchMainTab('redemption');
            setTimeout(() => {
                const card = document.getElementById('redemption-card-' + offerId);
                if (card) {
                    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    card.classList.add('ring-2', 'ring-emerald-500');
                    setTimeout(() => card.classList.remove('ring-2', 'ring-emerald-500'), 2500);
                }
            }, 120);
        }

        function renderRedemption() {
            const grid = document.getElementById('redemptionGrid');
            if (!grid) return;
            const searchInput = document.getElementById('redemptionSearchInput');
            const searchVal = (searchInput ? searchInput.value : '').toLowerCase().trim();
            const flowSelect = document.getElementById('redemptionFlowFilter');
            const flowVal = flowSelect ? flowSelect.value : 'all';
            const activeOffers = offersData.filter(o => o.status === 'Active');
            const filtered = activeOffers.filter(o => {
                if (flowVal !== 'all' && (o.application_flow_type || '').toLowerCase() !== flowVal.toLowerCase()) return false;
                if (searchVal) {
                    const haystack = [
                        o.title, o.platform, o.certification_name, o.checkout_field,
                        o.voucher_code, o.application_flow_type,
                        (o.redemption_guide ? o.redemption_guide.portal_name : '')
                    ].filter(Boolean).join(' ').toLowerCase();
                    if (!haystack.includes(searchVal)) return false;
                }
                return true;
            });

            const countEl = document.getElementById('redemptionResultsCount');
            if (countEl) countEl.textContent = 'Showing ' + filtered.length + ' of ' + activeOffers.length + ' verified redemption protocols';

            if (filtered.length === 0) {
                grid.innerHTML = '<div class="col-span-full p-8 text-center rounded-xl border" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">No voucher redemption paths match your active search or flow filter.</div>';
                return;
            }

            grid.innerHTML = filtered.map(o => {
                const guide = o.redemption_guide || {};
                const portalName = guide.portal_name || (o.platform + ' Checkout Portal');
                const portalUrl = guide.portal_url || o.url;
                const fieldLoc = guide.field_location || o.checkout_field || 'Billing Step -> Promo Code';
                const flowType = guide.flow_type || o.application_flow_type || 'Checkout Promo Code';
                const code = o.voucher_code || 'AUTO_APPLIED';
                const instructions = (guide.instructions && guide.instructions.length > 0) 
                    ? guide.instructions 
                    : [o.claim_steps || 'Complete training and apply discount code during checkout.'];

                const stepsHtml = instructions.map((s, idx) => `
                    <li class="flex items-start gap-2.5 text-xs leading-relaxed" style="color: var(--fg-default);">
                        <span class="w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5" style="background-color: var(--accent-subtle); color: var(--accent-fg); border: 1px solid var(--accent-fg);">${idx + 1}</span>
                        <span class="text-pretty">${s}</span>
                    </li>
                `).join('');

                return `
                <div class="primer-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between gap-4 border transition-all" id="redemption-card-${o.id}">
                    <div>
                        <div class="flex items-center justify-between gap-2 mb-2 flex-wrap">
                            <div class="flex items-center gap-2">
                                ${getPlatformIconSvg(o.platform)}
                                <span class="font-bold text-xs truncate" style="color: var(--fg-default);">${o.platform}</span>
                            </div>
                            <span class="text-[10px] px-2 py-0.5 rounded-full font-bold border" style="background-color: var(--accent-subtle); color: var(--accent-fg); border-color: var(--accent-fg);">${flowType}</span>
                        </div>

                        <h3 class="font-bold text-sm sm:text-base leading-snug tracking-tight" style="color: var(--fg-default);">${o.title}</h3>
                        
                        <!-- Checkout Field & Voucher Token Callout -->
                        <div class="mt-3 p-3 rounded-xl border" style="background-color: var(--canvas-inset); border-color: var(--border-default);">
                            <div class="text-[11px] font-semibold uppercase tracking-wider mb-1" style="color: var(--fg-muted);">Exact Checkout Field</div>
                            <div class="text-xs font-mono font-medium flex items-center gap-1.5" style="color: var(--fg-default);">
                                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" style="color: var(--accent-fg); flex-shrink: 0;"><path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-6.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM6.5 7.75A.75.75 0 0 1 7.25 7h1a.75.75 0 0 1 .75.75v2.75h.25a.75.75 0 0 1 0 1.5h-2.5a.75.75 0 0 1 0-1.5h.25v-2h-.25a.75.75 0 0 1-.75-.75ZM8 6a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"></path></svg>
                                <span class="text-pretty">${fieldLoc}</span>
                            </div>
                            <div class="mt-2.5 pt-2 border-t flex items-center justify-between gap-2 flex-wrap" style="border-color: var(--border-muted);">
                                <span class="text-[11px]" style="color: var(--fg-muted);">Voucher Token:</span>
                                <div class="flex items-center gap-1.5">
                                    <code class="px-1.5 py-0.5 rounded text-[11px] font-mono font-bold" style="background-color: var(--canvas-default); color: var(--accent-fg); border: 1px solid var(--border-default);">${code}</code>
                                    <button onclick="copyVoucherToken('${code}')" class="text-[10px] px-2 py-0.5 rounded border font-semibold transition active:scale-[0.95] cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">Copy</button>
                                </div>
                            </div>
                        </div>

                        <!-- Step-by-Step Checkout Flow -->
                        <div class="mt-3.5">
                            <div class="text-[11px] font-semibold uppercase tracking-wider mb-2" style="color: var(--fg-muted);">Redemption & Zero-Dollar Verification Steps</div>
                            <ul class="space-y-2">
                                ${stepsHtml}
                            </ul>
                        </div>
                    </div>

                    <!-- Verified Zero Balance Footer -->
                    <div class="pt-3 border-t flex items-center justify-between gap-2 mt-2 flex-wrap" style="border-color: var(--border-muted);">
                        <div class="flex items-center gap-2.5">
                            <div class="flex items-center gap-1.5 text-xs font-bold" style="color: var(--success-fg);">
                                <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor"><path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path></svg>
                                <span>Cart Balance: $0.00</span>
                            </div>
                            <button onclick="openProofModal('${o.id}')" class="text-xs font-semibold px-2.5 py-1 rounded-lg border hover:opacity-80 transition cursor-pointer inline-flex items-center gap-1" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);" title="View Verified Zero-Dollar Proof Lightbox">
                                📸 Proof
                            </button>
                        </div>
                        <a href="${portalUrl}" target="_blank" rel="noopener" class="text-xs font-semibold px-3 py-1.5 rounded-lg text-white transition active:scale-[0.98] inline-flex items-center gap-1 cursor-pointer" style="background-color: var(--btn-primary-bg);">
                            <span>Launch Portal</span>
                            <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M3.75 2h3.5a.75.75 0 0 1 0 1.5h-3.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-3.5a.75.75 0 0 1 1.5 0v3.5A1.75 1.75 0 0 1 12.25 14h-8.5A1.75 1.75 0 0 1 2 12.25v-8.5C2 2.784 2.784 2 3.75 2Zm6.75.75a.75.75 0 0 1 .75-.75h3.5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0V4.56L8.53 10.03a.75.75 0 0 1-1.06-1.06l5.47-5.47H11.25a.75.75 0 0 1-.75-.75Z"></path></svg>
                        </a>
                    </div>
                </div>`;
            }).join('');
        }

        // Initialize URL Query Params & Initial Load
        window.addEventListener('DOMContentLoaded', () => {
            const urlParams = new URLSearchParams(window.location.search);
            const viewParam = urlParams.get('view');
            const tabParam = urlParams.get('tab');

            setupSearchListener();

            const savedTheme = localStorage.getItem('certpulse_theme_v2') || localStorage.getItem('theme') || 'catppuccin-latte';
            applyTheme(savedTheme);
            updateGoalCounters();

            if (['grid', 'list', 'timeline', 'matrix'].includes(viewParam)) {
                setLayoutView(viewParam, false);
            } else {
                renderCards();
            }

            if (tabParam === 'news') {
                switchMainTab('news', false);
            } else if (tabParam === 'redemption') {
                switchMainTab('redemption', false);
            }
        });
"""

def generate_client_bundle(
    offers_json_str: str = "[]",
    news_json_str: str = "[]",
    last_sync_iso_js: str = "",
) -> str:
    """
    Compiles and returns the unified client-side JavaScript bundle.
    Safely substitutes serialized data payloads into the client runtime.
    """
    # Defensive fallbacks
    if not offers_json_str:
        offers_json_str = "[]"
    if not news_json_str:
        news_json_str = "[]"
    if not last_sync_iso_js:
        last_sync_iso_js = ""

    bundle = JS_TEMPLATE.replace("__OFFERS_DATA__", offers_json_str)
    bundle = bundle.replace("__NEWS_DATA__", news_json_str)
    bundle = bundle.replace("__LAST_SYNC_ISO__", last_sync_iso_js)
    return bundle
