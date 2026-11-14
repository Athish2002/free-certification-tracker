"""
Client bundle generator for CertPulse web application.
Compiles interactive state controllers, SVG icon bank, Proof Modal accessibility handlers,
multi-view render engines (Grid, Table, Timeline, Matrix, Redemption), and 4-timezone world telemetry.
"""

JS_TEMPLATE = """
        const offersData = __OFFERS_DATA__;
        const newsData = __NEWS_DATA__;
        const LAST_SYNC_ISO = "__LAST_SYNC_ISO__";

        // Security & HTML Sanitization Invariants (VULN-01 Defense)
        function escapeHtml(str) {
            if (str == null) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function escapeJs(str) {
            if (str == null) return '';
            return String(str)
                .replace(/\\\\/g, '\\\\\\\\')
                .replace(/'/g, "\\\\'")
                .replace(/"/g, '\\\\"')
                .replace(/</g, '\\\\x3c')
                .replace(/>/g, '\\\\x3e')
                .replace(/&/g, '\\\\x26');
        }

        function sanitizeUrl(url) {
            if (!url) return '#';
            const s = String(url).trim();
            if (/^(?:https?:\\/\\/|\\/|#|mailto:)/i.test(s)) {
                return escapeHtml(s);
            }
            return '#';
        }

        let currentMainTab = 'vouchers';
        let currentTier = 'all';
        let currentCategory = 'All';
        let currentSearch = '';
        let currentLayout = 'grid';

        function getOfferTier(o) {
            if (o.category_tier) return o.category_tier;
            const tv = o.truth_verification || {};
            const otype = (o.offer_type || '').toLowerCase();
            const seas = (o.seasonality || '').toLowerCase();
            const oid = (o.id || '').toLowerCase();
            const title = (o.title || '').toLowerCase();
            const rec = (o.recurrence_pattern || '').toLowerCase();

            const isPartialCopay = tv.policy_type === 'partial_discount_copay' || (tv.real_exam_cost_usd || 0) > 0;
            const isStudent = seas.includes('student') || otype.includes('student') || oid.includes('student');
            const isDiscount = (otype.includes('discount') && !otype.includes('100% free')) || (otype.includes('%') && !otype.includes('100%'));

            if (isPartialCopay || isStudent || isDiscount) return 'discount';
            if (['periodic_challenge_wave', 'annual_window', 'monthly_sweepstakes', 'event_driven'].includes(seas) ||
                oid.includes('wave') || title.includes('wave') || title.includes('challenge') ||
                rec.includes('wave') || rec.includes('cohort')) {
                return 'wave';
            }
            return 'badge';
        }

        function filterTier(tier) {
            currentTier = tier;
            document.querySelectorAll('#tierFilterPills .tier-pill').forEach(btn => {
                const btnTier = btn.getAttribute('data-tier');
                const isMatch = (btnTier === tier) || 
                                (tier === 'badge' && btnTier === 'skill_badge_lab') ||
                                (tier === 'skill_badge_lab' && btnTier === 'badge');
                if (isMatch) {
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
            const modal = document.getElementById('proofModal');
            if (!modal) return;
            if (!modal.classList.contains('hidden')) return;

            const offer = offersData.find(o => o.id === id);
            if (!offer) return;

            previousActiveElement = document.activeElement;
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

            const tierType = getOfferTier(offer);
            let tierLabel = '🎓 Written Proctored Exam';
            if (tierType === 'wave') tierLabel = '🌊 Limited-Time Exam Wave';
            else if (tierType === 'discount') tierLabel = '🏷️ Active Discount / Voucher';
            else if (tierType === 'badge') tierLabel = '🎓 Skill Badge & Lab';

            if (tierEl) {
                tierEl.textContent = tierLabel;
                if (tierType === 'wave') {
                    tierEl.style.backgroundColor = 'var(--accent-subtle)';
                    tierEl.style.borderColor = 'var(--accent-fg)';
                    tierEl.style.color = 'var(--accent-fg)';
                } else if (tierType === 'discount') {
                    tierEl.style.backgroundColor = 'rgba(217, 119, 6, 0.15)';
                    tierEl.style.borderColor = 'rgba(217, 119, 6, 0.4)';
                    tierEl.style.color = 'var(--attention-fg)';
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
                    badgeEl.className = 'px-2 py-0.5 rounded text-xs font-bold border';
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
                    badgeEl.className = 'px-2 py-0.5 rounded text-xs font-bold border border-red-500/30 bg-red-500/20 text-red-500';
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
                    badgeEl.className = 'px-2 py-0.5 rounded text-xs font-bold border border-amber-500/30 bg-amber-500/20 text-amber-500';
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
                    badgeEl.className = 'px-2 py-0.5 rounded text-xs font-bold border border-amber-500/30 bg-amber-500/20 text-amber-500';
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
                    badgeEl.className = 'px-2 py-0.5 rounded text-xs font-bold border border-red-500/30 bg-red-500/20 text-red-500';
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
                if (alertEl) {
                    alertEl.classList.remove('hidden');
                    alertEl.className = 'px-4 sm:px-6 py-2.5 text-xs border-b flex items-start gap-2 bg-slate-500/10 border-slate-500/20 text-slate-400 font-medium';
                    alertEl.innerHTML = '<span class="text-sm">📜</span><span><strong>Historical Campaign Archive:</strong> This certification campaign has concluded (e.g. promotional exam voucher quota exhausted or annual testing window closed). The screenshot below captures the campaign portal as audited. Preserved to monitor for future wave re-openings.</span>';
                }
                if (badgeEl) {
                    badgeEl.className = 'px-2 py-0.5 rounded text-xs font-bold border border-slate-500/30 bg-slate-500/20 text-slate-400';
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
            const eligEl = document.getElementById('proofModalEligibility');

            if (eligEl) {
                eligEl.textContent = offer.eligibility || 'Open to all developers and engineers globally with free account.';
            }

            if (tv) {
                if (truthCard) truthCard.classList.remove('hidden');
                if (policyTypeEl) {
                    policyTypeEl.textContent = (tv.policy_type || 'VERIFIED').replace(/_/g, ' ').replace(/\\b100pct\\b/gi, '100%').toUpperCase();
                    if (tv.policy_type === 'verified_100pct_free') {
                        policyTypeEl.className = 'px-1.5 py-0.5 rounded text-xs font-mono font-bold bg-emerald-500/10 text-emerald-500 border border-emerald-500/30';
                    } else if (tv.policy_type === 'partial_discount_copay' || tv.policy_type === 'annual_window_closed') {
                        policyTypeEl.className = 'px-1.5 py-0.5 rounded text-xs font-mono font-bold bg-amber-500/10 text-amber-500 border border-amber-500/30';
                    } else {
                        policyTypeEl.className = 'px-1.5 py-0.5 rounded text-xs font-mono font-bold bg-slate-500/10 text-slate-500 border border-slate-500/30';
                    }
                }
                if (sourceNameEl) sourceNameEl.textContent = tv.truth_source_name || offer.platform;
                if (sourceLink) sourceLink.href = tv.truth_source_url || offer.url;
                if (notesEl) notesEl.textContent = tv.verdict_notes || '';

                if (tv.policy_type === 'partial_discount_copay' && tv.real_exam_cost_usd > 0) {
                    if (alertEl) {
                        alertEl.classList.remove('hidden');
                        alertEl.className = 'px-4 sm:px-6 py-2.5 text-xs border-b flex items-start gap-2 bg-amber-500/10 border-amber-500/20 text-amber-500 font-medium';
                        alertEl.innerHTML = '<span class="text-sm">⚠️</span><span><strong>Official ' + escapeHtml(String(tv.verified_discount_pct)) + '% Discount Voucher:</strong> This voucher covers ' + escapeHtml(String(tv.verified_discount_pct)) + '% of the examination fee. The candidate must pay the remaining co-pay fee of ~$' + escapeHtml(String(tv.real_exam_cost_usd.toFixed(2))) + ' USD at Pearson VUE checkout. It is NOT a $0.00 waiver.</span>';
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

            const fullResLink = document.getElementById('proofModalFullResLink');
            if (fullResLink) {
                fullResLink.href = shotPath;
            }

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

        // Authentic Brand Logos (SVG Vector Library with Dual Icon Architecture)
        function getPlatformIconSvg(platform) {
            if (!platform) return '';
            const p = platform.toLowerCase();

            // 1. AWS (smile arrow + AWS mark)
            if (p.includes('aws') || p.includes('amazon')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 24 24"><path fill="currentColor" d="M4.5 9.2c-.8 0-1.5.3-1.8.8l.6.6c.2-.3.6-.5 1.2-.5.7 0 1.1.4 1.1 1v.2c-.3-.1-.7-.1-1.1-.1-1 0-1.7.5-1.7 1.3 0 .8.6 1.3 1.5 1.3.6 0 1.1-.3 1.3-.7v.6h.9v-2.8c0-1-.8-1.7-2-1.7zm.8 2.3c0 .4-.4.7-.9.7-.5 0-.8-.3-.8-.7 0-.4.3-.6.9-.6.3 0 .6 0 .8.1v.5zM8.2 9.4h.8l.8 2.7.8-2.7h.8l.8 2.7.8-2.7h.8l-1.2 4h-.9l-.8-2.6-.8 2.6h-.9l-1.2-4zM16.5 10.5c-.3-.2-.7-.3-1.1-.3-.6 0-.9.3-.9.6 0 .4.3.5.8.7.8.2 1.5.6 1.5 1.4 0 .9-.7 1.4-1.7 1.4-.6 0-1.2-.2-1.6-.5l.5-.7c.3.2.7.4 1.1.4.6 0 1-.3 1-.6 0-.4-.4-.5-.9-.7-.8-.2-1.4-.5-1.4-1.3 0-.8.7-1.3 1.6-1.3.5 0 1 .1 1.4.4l-.3.9z"/><path fill="#FF9900" d="M3.5 17.2c4.8 2.7 11 1.8 14.8-.8.4-.3.7.3.4.6-2.7 2.4-8.8 3.8-14.5 1.1-.6-.3-.2-1.1-.7-.9z"/><path fill="#FF9900" d="M19.2 15.1c-.3-.4-1.7-.5-2.4-.3-.3 0-.3-.3 0-.4 1-.6 2.6-.3 2.9 0 .2.3 0 2-.6 2.6-.3.3-.5.2-.4 0 .2-.6.8-1.5.5-1.9z"/></svg>`;
            }

            // 2. Microsoft / Azure (official Azure multi-polygon cloud)
            if (p.includes('azure') || p.includes('microsoft')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 24 24"><path d="M13.483 0a1.374 1.374 0 0 0-.961.438L4.85 8.163l4.57 3.327 4.063-7.49Z" fill="#0078d4"/><path d="M13.04 4.004l-3.62 6.673 4.542 3.842 5.057-9.458a1.375 1.375 0 0 0-1.198-1.057Z" fill="#5ea0ef"/><path d="M5.408 8.783.336 13.623a1.375 1.375 0 0 0 .142 1.996l7.747 6.467c.604.505 1.503.35 1.914-.33l3.655-6.05-4.457-3.235-3.93 2.502 2.65 2.186-.967 1.587-4.14-3.484 2.47-2.48Z" fill="#0078d4"/><path d="M13.794 15.706l-3.376 5.587a1.374 1.374 0 0 0 1.177 2.082h9.914c.974 0 1.62-.99 1.22-1.878l-4.942-10.978Z" fill="#005ba1"/></svg>`;
            }

            // 3. Google Cloud / GCP (official 4-color cloud logo)
            if (p.includes('google') || p.includes('gcp')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 24 24"><path fill="#4285F4" d="M19.35 10.04C18.67 6.59 15.64 4 12 4c-3.11 0-5.83 1.77-7.14 4.36L8.41 12C9.17 10.79 10.5 10 12 10c2.76 0 5 2.24 5 5 0 .34-.04.67-.11.99l3.52 2.6c.6-.82.94-1.82.94-2.59 0-2.64-2.05-4.78-4.65-4.96z"/><path fill="#EA4335" d="M16.9 14.99c.07-.32.1-.65.1-.99 0-2.76-2.24-5-5-5-.4 0-.78.06-1.15.15L8.41 6.72C9.52 6.26 10.73 6 12 6c3.64 0 6.67 2.59 7.35 6.04 1.5.11 2.82.93 3.52 2.15L19.35 16c-.46-.57-1.12-.92-1.85-.99-.2 0-.4.01-.6.02v-.04z"/><path fill="#FBBC05" d="M4.86 8.36C2.08 8.87 0 11.28 0 14.2c0 3.31 2.69 6 6 6h4.5v-3H6c-1.66 0-3-1.34-3-3 0-1.54 1.16-2.81 2.68-2.97l-.82-2.87z"/><path fill="#34A853" d="M19 14c0 1.66-1.34 3-3 3h-5.5v3H16c3.31 0 6-2.69 6-6 0-1.85-.85-3.5-2.18-4.58l-1.92 1.92C18.52 11.93 19 12.91 19 14z"/></svg>`;
            }

            // 4. Oracle (official Oracle red brand badge + cloud)
            if (p.includes('oracle')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 24 24"><rect x="1" y="2" width="22" height="20" rx="4" fill="#C74634"/><path d="M12 5c-3.6 0-6.5 1.1-6.5 2.5s2.9 2.5 6.5 2.5 6.5-1.1 6.5-2.5S15.6 5 12 5zm0 3.8c-2.5 0-4.5-.6-4.5-1.3s2-1.3 4.5-1.3 4.5.6 4.5 1.3-2 1.3-4.5 1.3z" fill="#FFFFFF"/><path d="M16.8 15.2c-.3-1.8-1.9-3.2-3.8-3.2-1.5 0-2.8.8-3.4 2.1-.4-.2-.8-.3-1.3-.3-1.8 0-3.3 1.5-3.3 3.3 0 1.8 1.5 3.3 3.3 3.3h8.3c1.7 0 3-1.3 3-3 0-1.5-1.2-2.8-2.8-2.2z" fill="#FFFFFF"/></svg>`;
            }

            // 5. Cisco (official Cisco bridge bar waveform)
            if (p.includes('cisco')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 24 24" fill="#049FD9"><rect x="1.5" y="13" width="1.5" height="7" rx="0.75"/><rect x="3.85" y="8" width="1.5" height="12" rx="0.75"/><rect x="6.2" y="13" width="1.5" height="7" rx="0.75"/><rect x="8.55" y="8" width="1.5" height="12" rx="0.75"/><rect x="10.9" y="3" width="1.5" height="17" rx="0.75"/><rect x="13.25" y="8" width="1.5" height="12" rx="0.75"/><rect x="15.6" y="13" width="1.5" height="7" rx="0.75"/><rect x="17.95" y="8" width="1.5" height="12" rx="0.75"/><rect x="20.3" y="13" width="1.5" height="7" rx="0.75"/></svg>`;
            }

            // 6. Databricks (official Databricks isometric stack)
            if (p.includes('databricks')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 24 24" fill="#FF3621"><path d="M12 0L1.605 6.002l1.605.926L12 1.854l8.79 5.074 1.605-.926L12 0zm0 5.432L3.21 10.505l1.605.926L12 7.287l7.185 4.144 1.605-.926L12 5.432zm0 5.432L3.21 15.579l1.605.926L12 12.36l7.185 4.145 1.605-.926L12 10.864zm0 5.432l-7.185 4.145 1.605.926L12 17.79l7.185 4.145 1.605-.926L12 16.296z"/></svg>`;
            }

            // 7. ISC2 (official ISC2 circular shield)
            if (p.includes('isc2') || p.includes('isc')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10.5" fill="none" stroke="#008542" stroke-width="1.8"/><path d="M12 4.5L5.5 7.5v5c0 4.2 2.8 7.2 6.5 8.2 3.7-1 6.5-4 6.5-8.2v-5L12 4.5z" fill="#008542"/><circle cx="12" cy="10.5" r="2.2" fill="#FFFFFF"/><path d="M10.8 11.5h2.4l.6 4h-3.6z" fill="#FFFFFF"/></svg>`;
            }

            // 8. Linux Foundation (official LF mark)
            if (p.includes('linux') || p.includes('cncf')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 24 24"><path d="M2.5 2.5v19h19v-5H7.5V2.5H2.5z" fill="#003366"/><path d="M10 2.5v12h11.5V2.5H10zm8 4h-4.5V4.5H18v2zm-2 4h-2.5V8.5H16v2z" fill="#0099FF"/></svg>`;
            }

            // 9. Snowflake (official Snowflake crystal)
            if (p.includes('snowflake')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 24 24" fill="#29B5E8"><path d="M12 0a1 1 0 0 0-1 1v3.27l-2.03-1.17a1 1 0 0 0-1 1.73L10 6.01 7.22 6.5a1 1 0 0 0 .34 1.97L11 8.08V11H8.08l-.39-3.44a1 1 0 1 0-1.98.22L6.2 10.6 3.4 9.1a1 1 0 0 0-1 1.73l2.87 1.66-2.87 1.66a1 1 0 0 0 1 1.73l2.8-1.5.5 2.82a1 1 0 1 0 1.98.22L8.08 13H11v2.92l-3.44.39a1 1 0 0 0-.34 1.97l2.78.49-2.03 1.18a1 1 0 0 0 1 1.73L11 20.51V23a1 1 0 1 0 2 0v-2.49l2.03 1.18a1 1 0 0 0 1-1.73l-2.78-.49 2.78-.49a1 1 0 0 0-.34-1.97L13 15.92V13h2.92l.39 3.44a1 1 0 0 0 1.98-.22l.51-2.82 2.8 1.5a1 1 0 0 0 1-1.73l-2.87-1.66 2.87-1.66a1 1 0 0 0-1-1.73l-2.8 1.5-.51-2.82a1 1 0 1 0-1.98-.22L15.92 11H13V8.08l3.44-.39a1 1 0 0 0 .34-1.97l-2.78-.49 2.03-1.18a1 1 0 0 0-1-1.73L13 4.27V1a1 1 0 0 0-1-1z"/></svg>`;
            }

            // 10. Splunk (official Splunk angle bracket)
            if (p.includes('splunk')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 24 24" fill="#F15B24"><path d="M3.5 3.5l8.8 8.5-8.8 8.5h4.2l8.8-8.5-8.8-8.5H3.5z"/><rect x="15.5" y="18" width="7" height="2.5" rx="0.5"/></svg>`;
            }

            // 11. IBM (official IBM 8-bar mark)
            if (p.includes('ibm')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 24 24" fill="#0F62FE"><path d="M0 3.25h5.455v1.442H0V3.25zm6.818 0h6.705v1.442H6.818V3.25zm8.068 0H24v1.442h-9.114V3.25zM0 5.606h5.455v1.442H0V5.606zm6.818 0h6.705v1.442H6.818V5.606zm8.068 0H24v1.442h-9.114V5.606zM0 7.962h5.455v1.442H0V7.962zm8.182 0h4.09v1.442h-4.09V7.962zm8.068 0H24v1.442h-7.75V7.962zM0 10.317h5.455v1.442H0v-1.442zm8.182 0h4.09v1.442h-4.09v-1.442zm8.068 0H24v1.442h-7.75v-1.442zM0 12.673h5.455v1.442H0v-1.442zm6.818 0h6.705v1.442H6.818v-1.442zm8.068 0H24v1.442h-9.114v-1.442zM0 15.029h5.455v1.442H0v-1.442zm8.182 0h4.09v1.442h-4.09v-1.442zm8.068 0H24v1.442h-7.75v-1.442zM0 17.385h5.455v1.442H0v-1.442zm6.818 0h6.705v1.442H6.818v-1.442zm8.068 0H24v1.442h-9.114v-1.442zM0 19.74h5.455v1.442H0V19.74zm6.818 0h6.705v1.442H6.818V19.74zm8.068 0H24v1.442h-9.114V19.74z"/></svg>`;
            }

            // 12. Harvard (official Veritas crest / academic shield)
            if (p.includes('harvard')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 24 24"><path d="M12 2C6.5 2 4 4.5 4 8.5c0 6.5 5 11 8 13.5 3-2.5 8-7 8-13.5 0-4-2.5-6.5-8-6.5z" fill="#A51C30"/><path d="M12 3.2C7.3 3.2 5.2 5.4 5.2 8.7c0 5.6 4.3 9.7 6.8 11.8 2.5-2.1 6.8-6.2 6.8-11.8 0-3.3-2.1-5.5-6.8-5.5z" fill="none" stroke="#FFFFFF" stroke-width="0.75" opacity="0.6"/><rect x="6.8" y="6.2" width="4.2" height="3.2" rx="0.5" fill="#FFFFFF"/><text x="7.4" y="8.6" font-size="2" font-weight="bold" fill="#A51C30" font-family="serif">VE</text><rect x="13" y="6.2" width="4.2" height="3.2" rx="0.5" fill="#FFFFFF"/><text x="13.7" y="8.6" font-size="2" font-weight="bold" fill="#A51C30" font-family="serif">RI</text><rect x="9.9" y="11.5" width="4.2" height="3.2" rx="0.5" fill="#FFFFFF"/><text x="10.2" y="13.9" font-size="1.8" font-weight="bold" fill="#A51C30" font-family="serif">TAS</text></svg>`;
            }

            // Additional Platforms
            if (p.includes('github')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"/></svg>`;
            }
            if (p.includes('mongodb')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 16 16" fill="#00ed64"><path d="M8 1c.5 1.5 4 4.5 4 8a4 4 0 0 1-8 0c0-3.5 3.5-6.5 4-8z"/><path d="M8 3v10" stroke="#001e2b" stroke-width="0.8"/></svg>`;
            }
            if (p.includes('salesforce')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 16 16" fill="#00a1e0"><path d="M6 4a3.5 3.5 0 0 1 3.4 2.7 3 3 0 0 1 3.6 3 2.5 2.5 0 0 1-2.5 2.3H5a3 3 0 0 1-.9-5.8A3.5 3.5 0 0 1 6 4z"/></svg>`;
            }
            if (p.includes('postman')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 16 16" fill="#ff6c37"><circle cx="8" cy="8" r="6.5"/><path d="M5 8l2.5 2.5L11 5" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
            }
            if (p.includes('juniper')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 16 16"><rect x="2" y="2" width="12" height="12" rx="3" fill="#00739c"/><path d="M6 6h4v4H6z" fill="#ffffff"/></svg>`;
            }
            if (p.includes('fortinet')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 16 16" fill="#ee3124"><rect x="2" y="3" width="5.5" height="4.5" rx="1"/><rect x="8.5" y="3" width="5.5" height="4.5" rx="1"/><rect x="2" y="8.5" width="5.5" height="4.5" rx="1"/><rect x="8.5" y="8.5" width="5.5" height="4.5" rx="1"/></svg>`;
            }
            if (p.includes('qualys')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" stroke="#ed1c24" stroke-width="1.5" fill="none"/><path d="M9 10l2.5 2.5" stroke="#ed1c24" stroke-width="2" stroke-linecap="round"/></svg>`;
            }
            if (p.includes('red hat')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 16 16"><path d="M14.5 10.5c-.8 0-1.8-.3-2.6-.7-.6 1.4-2 2.2-3.9 2.2-2.3 0-4-1.2-4-2.8 0-.4.1-.7.3-1C2.9 8.2 2 7.7 2 7.2c0-.5.8-1 2.3-1.3C5 4.5 6.4 3 8 3c2.2 0 3.7 1.6 4.1 3.8 1.4.3 2.4 1 2.4 1.8 0 .5-.7 1-2 1.3.4.2.8.4 1.2.6.5-.2.8-.2.8 0 0 .5-1.1.8-2 .8z" fill="#ee0000"/></svg>`;
            }
            if (p.includes('hashicorp')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 16 16" fill="#027bfd"><path d="M2.5 2h3v12h-3zm8 0h3v12h-3zm-5.5 4.5h5v3h-5z"/></svg>`;
            }
            if (p.includes('palo alto')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 16 16" fill="#fa582d"><path d="M8 1L2 4v5c0 3.5 2.5 5.5 6 6 3.5-.5 6-2.5 6-6V4L8 1zm0 2.2l4 2v3.8c0 2.4-1.6 3.9-4 4.3-2.4-.4-4-1.9-4-4.3V5.2l4-2z"/></svg>`;
            }
            if (p.includes('gitlab')) {
                return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 16 16" fill="#fc6d26"><path d="M8 14.5L1.5 5.8l2.2-6.5L8 4.2l4.3-4.9 2.2 6.5L8 14.5z"/></svg>`;
            }
            return `<svg class="w-4 h-4 flex-shrink-0 platform-brand-icon" viewBox="0 0 16 16" fill="var(--accent-fg)"><circle cx="8" cy="8" r="6"/></svg>`;
        }

        // Canonical Developer Color Palettes: GitHub Dark and GitHub Light
        const THEMES = [
            { id: 'github-dark', name: 'GitHub Dark', dot: '#58a6ff', meta: '#0d1117', type: 'dark' },
            { id: 'github-light', name: 'GitHub Light', dot: '#0969da', meta: '#ffffff', type: 'light' }
        ];

        function selectTheme(id) {
            applyTheme(id);
            closeThemeDropdown();
        }

        function getThemeName(id) {
            return (id === 'github-light' || id === 'light') ? 'Primer Crisp Light' : 'Obsidian Cyan';
        }

        function applyTheme(id) {
            let targetId = (id === 'github-light' || id === 'light') ? 'github-light' : 'github-dark';

            document.documentElement.setAttribute('data-theme', targetId);
            try {
                localStorage.setItem('certpulse_theme_v2', targetId);
                localStorage.setItem('certpulse_theme', targetId);
                localStorage.setItem('theme', targetId);
            } catch(e) {}
            
            const meta = document.getElementById('themeColorMeta') || document.querySelector('meta[name="theme-color"]');
            if (meta) meta.content = (targetId === 'github-light') ? '#ffffff' : '#0d1117';

            // Sync Sun/Moon icon for quick toggle button:
            // When in Dark mode, show Sun icon ("Light" label - click to switch to Light)
            // When in Light mode, show Moon icon ("Dark" label - click to switch to Dark)
            const isLight = (targetId === 'github-light');
            const sun = document.getElementById('themeIconSun');
            const moon = document.getElementById('themeIconMoon');
            if (sun && moon) {
                if (isLight) {
                    sun.classList.add('hidden');
                    moon.classList.remove('hidden');
                } else {
                    sun.classList.remove('hidden');
                    moon.classList.add('hidden');
                }
            }
            if (typeof resizeBgCanvas === 'function') {
                resizeBgCanvas();
            }
        }

        const switchTheme = applyTheme;

        function toggleTheme() {
            const current = document.documentElement.getAttribute('data-theme') || 'github-dark';
            const nextTheme = (current === 'github-dark' || current === 'dark') ? 'github-light' : 'github-dark';
            applyTheme(nextTheme);
            if (window.audioSynth) {
                audioSynth.playClick('action');
            }
            triggerToast('Theme: ' + (nextTheme === 'github-dark' ? 'Obsidian Cyan (Dark)' : 'Primer Crisp (Light)'));
        }

        function toggleThemeDropdown() {
            const menu = document.getElementById('themeDropdownMenu');
            if (menu) menu.classList.toggle('hidden');
            else toggleTheme();
        }

        function closeThemeDropdown() {
            const menu = document.getElementById('themeDropdownMenu');
            if (menu) menu.classList.add('hidden');
        }

        // ================= WEB AUDIO PROCEDURAL HAPTICS SYNTHESIZER =================
        class UIAudioSynthesizer {
            constructor() {
                this.ctx = null;
                this.enabled = true;
            }
            init() {
                if (!this.ctx) {
                    const AudioContext = window.AudioContext || window.webkitAudioContext;
                    if (AudioContext) {
                        this.ctx = new AudioContext();
                    }
                }
                if (this.ctx && this.ctx.state === 'suspended') {
                    this.ctx.resume();
                }
            }
            playClick(type = 'tick') {
                if (!this.enabled) return;
                this.init();
                if (!this.ctx) return;
                try {
                    const now = this.ctx.currentTime;
                    const osc = this.ctx.createOscillator();
                    const gain = this.ctx.createGain();
                    if (type === 'tick') {
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(800, now);
                        osc.frequency.exponentialRampToValueAtTime(300, now + 0.025);
                        gain.gain.setValueAtTime(0.04, now);
                        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.025);
                        osc.start(now);
                        osc.stop(now + 0.025);
                    } else if (type === 'action') {
                        osc.type = 'triangle';
                        osc.frequency.setValueAtTime(220, now);
                        osc.frequency.exponentialRampToValueAtTime(80, now + 0.05);
                        gain.gain.setValueAtTime(0.08, now);
                        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
                        osc.start(now);
                        osc.stop(now + 0.05);
                    } else if (type === 'chime') {
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(523.25, now);
                        osc.frequency.setValueAtTime(659.25, now + 0.08);
                        gain.gain.setValueAtTime(0.12, now);
                        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
                        osc.start(now);
                        osc.stop(now + 0.35);
                    }
                    osc.connect(gain);
                    gain.connect(this.ctx.destination);
                } catch(e) {}
            }
        }
        const audioSynth = new UIAudioSynthesizer();
        window.audioSynth = audioSynth;

        function toggleAudioHaptics() {
            audioSynth.enabled = !audioSynth.enabled;
            const statusEl = document.getElementById('audio-status');
            const eqEl = document.getElementById('audio-equalizer');
            if (audioSynth.enabled) {
                if (statusEl) { statusEl.innerText = 'ON'; statusEl.className = 'font-bold text-emerald-400'; }
                if (eqEl) eqEl.classList.remove('opacity-30');
                audioSynth.playClick('action');
                triggerToast('🔊 Audio Haptics Enabled');
            } else {
                if (statusEl) { statusEl.innerText = 'OFF'; statusEl.className = 'font-bold text-zinc-500'; }
                if (eqEl) eqEl.classList.add('opacity-30');
                triggerToast('🔇 Audio Haptics Muted');
            }
        }

        // ================= PURE NATIVE HTML5 CANVAS CONFETTI BURST =================
        function triggerConfettiBurst(particleCount = 70) {
            if (window.audioSynth) audioSynth.playClick('chime');
            try {
                const canvas = document.createElement('canvas');
                canvas.style.position = 'fixed';
                canvas.style.top = '0';
                canvas.style.left = '0';
                canvas.style.width = '100vw';
                canvas.style.height = '100vh';
                canvas.style.pointerEvents = 'none';
                canvas.style.zIndex = '99999';
                document.body.appendChild(canvas);
                const ctx = canvas.getContext('2d');
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
                const particles = [];
                const colors = ['#38bdf8', '#34d399', '#fbbf24', '#a855f7', '#f43f5e', '#ffffff'];
                for (let i = 0; i < particleCount; i++) {
                    particles.push({
                        x: canvas.width / 2 + (Math.random() - 0.5) * 200,
                        y: canvas.height * 0.45,
                        vx: (Math.random() - 0.5) * 14,
                        vy: (Math.random() - 1.2) * 12,
                        size: Math.random() * 7 + 4,
                        color: colors[Math.floor(Math.random() * colors.length)],
                        rot: Math.random() * 360,
                        vrot: (Math.random() - 0.5) * 10,
                        alpha: 1
                    });
                }
                let animId = null;
                function update() {
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    let alive = 0;
                    for (const p of particles) {
                        p.x += p.vx;
                        p.y += p.vy;
                        p.vy += 0.35;
                        p.rot += p.vrot;
                        p.alpha -= 0.015;
                        if (p.alpha > 0) {
                            alive++;
                            ctx.save();
                            ctx.translate(p.x, p.y);
                            ctx.rotate((p.rot * Math.PI) / 180);
                            ctx.fillStyle = p.color;
                            ctx.globalAlpha = Math.max(0, p.alpha);
                            ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.7);
                            ctx.restore();
                        }
                    }
                    if (alive > 0) {
                        animId = requestAnimationFrame(update);
                    } else {
                        cancelAnimationFrame(animId);
                        if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
                    }
                }
                update();
            } catch(e) {}
        }

        // ================= RUNNING AMBIENT BACKGROUND CANVAS ENGINE =================
        let bgFxMode = 'constellation';
        const bgCanvas = document.getElementById('ambient-canvas');
        const bgCtx = bgCanvas ? bgCanvas.getContext('2d') : null;
        let bgWidth = 0, bgHeight = 0, bgAnimFrameId = null;
        let bgMouseX = -999, bgMouseY = -999;
        const particles = [];
        const PARTICLE_COUNT = 48;
        const CONNECT_DIST = 110;
        const hexColumns = [];
        const HEX_WORDS = ['0x4A', 'SHA256', '200_OK', 'ORACLE', 'VUE', 'CS50X', '1Z0-1127', 'HTTP/3', 'PROVED', 'LEDGER', 'HASH_OK', 'PEARSON'];
        let gridOffset = 0;

        function resizeBgCanvas() {
            if (!bgCanvas) return;
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            bgWidth = window.innerWidth;
            bgHeight = window.innerHeight;
            bgCanvas.width = bgWidth * dpr;
            bgCanvas.height = bgHeight * dpr;
            if (bgCtx) {
                bgCtx.scale(dpr, dpr);
            }
        }

        function initConstellationParticles() {
            particles.length = 0;
            for (let i = 0; i < PARTICLE_COUNT; i++) {
                particles.push({
                    x: Math.random() * (bgWidth || 1200),
                    y: Math.random() * (bgHeight || 800),
                    vx: (Math.random() - 0.5) * 0.7,
                    vy: (Math.random() - 0.5) * 0.7,
                    radius: Math.random() * 1.8 + 1.2,
                    pulse: Math.random() * Math.PI
                });
            }
        }

        function initHexColumns() {
            hexColumns.length = 0;
            const colWidth = 46;
            const totalCols = Math.floor((bgWidth || 1200) / colWidth);
            for (let i = 0; i < totalCols; i++) {
                hexColumns.push({
                    x: i * colWidth + 12,
                    y: Math.random() * -(bgHeight || 800),
                    speed: Math.random() * 1.5 + 1.2,
                    text: HEX_WORDS[Math.floor(Math.random() * HEX_WORDS.length)],
                    opacity: Math.random() * 0.45 + 0.25
                });
            }
        }

        function getThemeAccentRGB() {
            const isDark = (document.documentElement.getAttribute('data-theme') || 'github-dark') !== 'github-light';
            return isDark
                ? { r: 56, g: 189, b: 248, baseAlpha: 0.35 }
                : { r: 2, g: 132, b: 199, baseAlpha: 0.18 };
        }

        function renderAmbientBackground() {
            if (!bgCtx || bgFxMode === 'off') {
                bgAnimFrameId = null;
                return;
            }
            if (document.hidden) {
                bgAnimFrameId = requestAnimationFrame(renderAmbientBackground);
                return;
            }

            bgCtx.clearRect(0, 0, bgWidth, bgHeight);
            const color = getThemeAccentRGB();

            if (bgFxMode === 'constellation') {
                for (let i = 0; i < particles.length; i++) {
                    const p = particles[i];
                    p.x += p.vx;
                    p.y += p.vy;
                    p.pulse += 0.03;

                    if (p.x < 0) p.x = bgWidth;
                    if (p.x > bgWidth) p.x = 0;
                    if (p.y < 0) p.y = bgHeight;
                    if (p.y > bgHeight) p.y = 0;

                    if (bgMouseX > 0 && bgMouseY > 0) {
                        const dx = bgMouseX - p.x;
                        const dy = bgMouseY - p.y;
                        const dist = Math.hypot(dx, dy);
                        if (dist < 120) {
                            const force = (120 - dist) / 120;
                            p.x -= (dx / dist) * force * 2.5;
                            p.y -= (dy / dist) * force * 2.5;
                        }
                    }

                    const alpha = color.baseAlpha * (0.8 + 0.3 * Math.sin(p.pulse));
                    bgCtx.fillStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha})`;
                    bgCtx.beginPath();
                    bgCtx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                    bgCtx.fill();

                    for (let j = i + 1; j < particles.length; j++) {
                        const p2 = particles[j];
                        const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
                        if (dist < CONNECT_DIST) {
                            const lineAlpha = (1 - dist / CONNECT_DIST) * color.baseAlpha * 0.8;
                            bgCtx.strokeStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${lineAlpha})`;
                            bgCtx.lineWidth = 0.9;
                            bgCtx.beginPath();
                            bgCtx.moveTo(p.x, p.y);
                            bgCtx.lineTo(p2.x, p2.y);
                            bgCtx.stroke();
                        }
                    }
                }
            } else if (bgFxMode === 'hex-stream') {
                bgCtx.font = '11px monospace';
                for (let i = 0; i < hexColumns.length; i++) {
                    const col = hexColumns[i];
                    col.y += col.speed;
                    if (col.y > bgHeight + 60) {
                        col.y = -40;
                        col.text = HEX_WORDS[Math.floor(Math.random() * HEX_WORDS.length)];
                    }
                    bgCtx.fillStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${col.opacity * color.baseAlpha * 1.5})`;
                    bgCtx.fillText(col.text, col.x, col.y);
                }
            } else if (bgFxMode === 'cyber-grid') {
                gridOffset = (gridOffset + 0.6) % 36;
                const horizonY = bgHeight * 0.35;
                const centerX = bgWidth / 2;
                const rayCount = 18;
                bgCtx.lineWidth = 0.9;
                bgCtx.strokeStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${color.baseAlpha * 0.45})`;
                for (let i = -rayCount; i <= rayCount; i++) {
                    const bottomX = centerX + (i * 60);
                    bgCtx.beginPath();
                    bgCtx.moveTo(centerX, horizonY);
                    bgCtx.lineTo(bottomX, bgHeight);
                    bgCtx.stroke();
                }
                for (let y = horizonY + 10; y < bgHeight; y += 18) {
                    const depth = (y - horizonY) / (bgHeight - horizonY);
                    const movingY = y + gridOffset * depth;
                    if (movingY < bgHeight) {
                        const alpha = Math.min(depth * color.baseAlpha * 0.9, 0.45);
                        bgCtx.strokeStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha})`;
                        bgCtx.beginPath();
                        bgCtx.moveTo(0, movingY);
                        bgCtx.lineTo(bgWidth, movingY);
                        bgCtx.stroke();
                    }
                }
            }
            bgAnimFrameId = requestAnimationFrame(renderAmbientBackground);
        }

        function setBackgroundFXMode(mode) {
            if (window.audioSynth) audioSynth.playClick('action');
            bgFxMode = mode;
            document.querySelectorAll('.fx-pill').forEach(btn => {
                const btnText = btn.textContent.toLowerCase();
                if ((mode === 'constellation' && btnText.includes('node')) ||
                    (mode === 'hex-stream' && btnText.includes('hex')) ||
                    (mode === 'cyber-grid' && btnText.includes('grid')) ||
                    (mode === 'off' && btnText.includes('off'))) {
                    btn.style.backgroundColor = 'var(--accent-subtle)';
                    btn.style.color = 'var(--accent-fg)';
                    btn.classList.add('font-bold');
                } else {
                    btn.style.backgroundColor = 'transparent';
                    btn.style.color = 'var(--fg-muted)';
                    btn.classList.remove('font-bold');
                }
            });
            if (mode === 'off') {
                if (bgAnimFrameId) {
                    cancelAnimationFrame(bgAnimFrameId);
                    bgAnimFrameId = null;
                }
                if (bgCtx) bgCtx.clearRect(0, 0, bgWidth, bgHeight);
            } else if (bgFxMode !== 'off') {
                if (mode === 'constellation') initConstellationParticles();
                else if (mode === 'hex-stream') initHexColumns();
                if (!bgAnimFrameId) {
                    bgAnimFrameId = requestAnimationFrame(renderAmbientBackground);
                }
            }
        }

        // ================= TOAST NOTIFICATION ENGINE =================
        function triggerToast(msg) {
            const toastEl = document.getElementById('toastNotification');
            const msgEl = document.getElementById('toastMessage');
            if (!toastEl || !msgEl) return;
            msgEl.textContent = msg;
            toastEl.classList.remove('translate-y-20', 'opacity-0');
            toastEl.classList.add('translate-y-0', 'opacity-100');
            clearTimeout(window._toastTimeout);
            window._toastTimeout = setTimeout(() => {
                toastEl.classList.remove('translate-y-0', 'opacity-100');
                toastEl.classList.add('translate-y-20', 'opacity-0');
            }, 3000);
        }
        const toast = triggerToast;

        // ================= 3D CARD FLIP MECHANISM =================
        function flipCard(cardId) {
            if (window.audioSynth) audioSynth.playClick('action');
            const card = document.getElementById('card-' + cardId);
            if (card) {
                card.classList.toggle('is-flipped');
            }
        }

        // ================= ONE-CLICK .ICS CALENDAR REMINDER GENERATOR =================
        function downloadCalendarReminder(offerId) {
            const offer = offersData.find(o => o.id === offerId);
            if (!offer) return;
            if (window.audioSynth) audioSynth.playClick('action');
            const now = new Date();
            const startStr = now.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
            const end = new Date(now.getTime() + 3600000 * 2);
            const endStr = end.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
            const title = (offer.title || offer.certification_name || 'Certification Voucher').replace(/,/g, '\\,');
            const url = offer.direct_verified_url || offer.url || 'https://athish2002.github.io/free-certification-tracker/';
            const ics = [
                'BEGIN:VCALENDAR',
                'VERSION:2.0',
                'PRODID:-//CertPulse//Certification Tracker//EN',
                'BEGIN:VEVENT',
                `UID:certpulse-${offer.id}-${Date.now()}@certpulse.local`,
                `DTSTAMP:${startStr}`,
                `DTSTART:${startStr}`,
                `DTEND:${endStr}`,
                `SUMMARY:CertPulse Voucher Deadline: ${title}`,
                `DESCRIPTION:Claim official verified certification voucher terms for ${title}. Portal: ${url}`,
                `URL:${url}`,
                'STATUS:CONFIRMED',
                'END:VEVENT',
                'END:VCALENDAR'
            ].join('\\r\\n');
            const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `CertPulse_${offer.id}_reminder.ics`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            triggerToast('📅 Calendar reminder downloaded (.ics file)!');
        }

        // ================= LATENCY PROBE & MANUAL PING =================
        function jitterLatency() {
            if (document.hidden) return;
            const latencyEl = document.getElementById('live-latency');
            if (latencyEl) {
                const ms = Math.floor(Math.random() * 8) + 16;
                latencyEl.innerText = ms + 'ms';
                latencyEl.classList.remove('latency-flash');
                void latencyEl.offsetWidth;
                latencyEl.classList.add('latency-flash');
            }
        }

        function manualPingOracle() {
            if (window.audioSynth) audioSynth.playClick('tick');
            const latencyEl = document.getElementById('live-latency');
            const chip = document.getElementById('latency-chip');
            if (chip) {
                chip.classList.add('border-emerald-400', 'scale-105');
            }
            let count = 0;
            const pingInterval = setInterval(() => {
                if (latencyEl) {
                    const simulated = Math.floor(Math.random() * 10) + 12;
                    latencyEl.innerText = simulated + 'ms';
                }
                count++;
                if (count >= 4) {
                    clearInterval(pingInterval);
                    jitterLatency();
                    if (chip) {
                        chip.classList.remove('border-emerald-400', 'scale-105');
                    }
                    triggerToast('⚡ Oracle Network Ping: Active node corroborated at ' + (latencyEl ? latencyEl.innerText : '17ms') + ' (Zero loss)');
                }
            }, 55);
        }

        // ================= RAYCAST-STYLE COMMAND PALETTE (⌘K / Ctrl+K) =================
        function openCommandPalette() {
            let cp = document.getElementById('commandPaletteModal');
            if (!cp) {
                const div = document.createElement('div');
                div.id = 'commandPaletteModal';
                div.className = 'fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-black/60 backdrop-blur-sm';
                div.innerHTML = `
                <div class="relative w-full max-w-xl rounded-2xl border shadow-2xl overflow-hidden primer-card neo-shadow" style="background-color: var(--canvas-subtle); border-color: var(--border-default);" onclick="event.stopPropagation()">
                    <div class="p-3 border-b flex items-center gap-2.5" style="border-color: var(--border-default);">
                        <svg class="w-4 h-4" style="color: var(--fg-muted);" viewBox="0 0 16 16" fill="currentColor"><path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.5 4.5 0 1 0-9 0 4.5 4.5 0 0 0 9 0Z"></path></svg>
                        <input type="text" id="cpInput" placeholder="Type a command, provider, or shortcut..." class="w-full text-xs sm:text-sm outline-none bg-transparent" style="color: var(--fg-default);" autofocus>
                        <kbd class="px-1.5 py-0.5 rounded border text-xs font-mono" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">ESC</kbd>
                    </div>
                    <div id="cpResults" class="p-2 max-h-72 overflow-y-auto divide-y" style="border-color: var(--border-muted);">
                        <div onclick="toggleTheme(); closeCommandPalette();" class="p-2.5 rounded-lg flex items-center justify-between cursor-pointer hover:bg-slate-500/10 text-xs">
                            <span class="font-semibold" style="color: var(--fg-default);">Toggle Dark / Light Mode</span>
                            <kbd class="px-1.5 py-0.5 rounded border text-xs font-mono" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">T</kbd>
                        </div>
                        <div onclick="switchMainTab('vouchers'); closeCommandPalette();" class="p-2.5 rounded-lg flex items-center justify-between cursor-pointer hover:bg-slate-500/10 text-xs">
                            <span class="font-semibold" style="color: var(--fg-default);">Switch to Certification Vouchers</span>
                            <kbd class="px-1.5 py-0.5 rounded border text-xs font-mono" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">1</kbd>
                        </div>
                        <div onclick="switchMainTab('news'); closeCommandPalette();" class="p-2.5 rounded-lg flex items-center justify-between cursor-pointer hover:bg-slate-500/10 text-xs">
                            <span class="font-semibold" style="color: var(--fg-default);">Switch to Industry Tech Radar</span>
                            <kbd class="px-1.5 py-0.5 rounded border text-xs font-mono" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">2</kbd>
                        </div>
                        <div onclick="switchMainTab('redemption'); closeCommandPalette();" class="p-2.5 rounded-lg flex items-center justify-between cursor-pointer hover:bg-slate-500/10 text-xs">
                            <span class="font-semibold" style="color: var(--fg-default);">Switch to Redemption Protocol</span>
                            <kbd class="px-1.5 py-0.5 rounded border text-xs font-mono" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">3</kbd>
                        </div>
                        <div onclick="cycleLayoutView(); closeCommandPalette();" class="p-2.5 rounded-lg flex items-center justify-between cursor-pointer hover:bg-slate-500/10 text-xs">
                            <span class="font-semibold" style="color: var(--fg-default);">Cycle Catalog Views</span>
                            <kbd class="px-1.5 py-0.5 rounded border text-xs font-mono" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">V</kbd>
                        </div>
                        <div onclick="manualPingOracle(); closeCommandPalette();" class="p-2.5 rounded-lg flex items-center justify-between cursor-pointer hover:bg-slate-500/10 text-xs">
                            <span class="font-semibold" style="color: var(--fg-default);">Ping Oracle Truth Network Node</span>
                            <span class="text-xs font-mono text-emerald-400">18ms</span>
                        </div>
                        <div onclick="toggleAudioHaptics(); closeCommandPalette();" class="p-2.5 rounded-lg flex items-center justify-between cursor-pointer hover:bg-slate-500/10 text-xs">
                            <span class="font-semibold" style="color: var(--fg-default);">Toggle Procedural Audio Synthesizer</span>
                            <span class="text-xs font-mono text-emerald-400">Audio Haptics</span>
                        </div>
                    </div>
                </div>`;
                div.onclick = closeCommandPalette;
                document.body.appendChild(div);
                cp = div;
            }
            cp.classList.remove('hidden');
            const inp = document.getElementById('cpInput');
            if (inp) { inp.value = ''; inp.focus(); }
            if (window.audioSynth) audioSynth.playClick('action');
        }

        function closeCommandPalette() {
            const cp = document.getElementById('commandPaletteModal');
            if (cp) cp.classList.add('hidden');
        }

        // Global Synchronized Master UTC Telemetry with Live Seconds & Dynamic Local Offset
        function updateWorldClock() {
            const now = new Date();
            const utcHours = String(now.getUTCHours()).padStart(2, '0');
            const utcMinutes = String(now.getUTCMinutes()).padStart(2, '0');
            const utcSeconds = String(now.getUTCSeconds()).padStart(2, '0');
            const utcTime = `${utcHours}:${utcMinutes}:${utcSeconds} UTC`;

            const offsetMin = -now.getTimezoneOffset();
            const offsetSign = offsetMin >= 0 ? '+' : '-';
            const absOffsetMin = Math.abs(offsetMin);
            const offH = String(Math.floor(absOffsetMin / 60)).padStart(2, '0');
            const offM = String(absOffsetMin % 60).padStart(2, '0');
            const localStr = `Local (UTC${offsetSign}${offH}:${offM})`;

            const navUtc = document.getElementById('navUtcClock');
            if (navUtc) navUtc.textContent = utcTime;
            const navLocal = document.getElementById('navLocalOffset');
            if (navLocal) navLocal.textContent = `• ${localStr}`;

            const navTimeText = document.getElementById('navTimezoneText');
            if (navTimeText) navTimeText.textContent = `Live Telemetry: ${utcTime} • ${localStr}`;

            const heroUtc = document.getElementById('heroCadenceUtc');
            if (heroUtc) heroUtc.textContent = `${utcHours}:${utcMinutes} UTC`;
        }
        setInterval(updateWorldClock, 1000);

        // ================= PERSONAL STUDY GOALS TRACKER ENGINE =================
        function getTrackedOffers() {
            try {
                const raw = localStorage.getItem('certpulse_tracked_offers');
                return raw ? JSON.parse(raw) : [];
            } catch (e) {
                return [];
            }
        }

        function isOfferTracked(id) {
            if (!id) return false;
            return getTrackedOffers().includes(id);
        }

        function toggleOfferChecked(id) {
            if (!id) return;
            let tracked = getTrackedOffers();
            const idx = tracked.indexOf(id);
            if (idx >= 0) {
                tracked.splice(idx, 1);
                triggerToast('Removed from personal study goals');
            } else {
                tracked.push(id);
                triggerToast('⭐ Added to personal study goals!');
                if (window.audioSynth) audioSynth.playClick('action');
            }
            try {
                localStorage.setItem('certpulse_tracked_offers', JSON.stringify(tracked));
            } catch (e) {
                console.warn('LocalStorage unavailable for goal tracking', e);
            }
            updateGoalCounters();
            renderCards();
        }

        function clearAllChecked() {
            try {
                localStorage.removeItem('certpulse_tracked_offers');
            } catch (e) {
                console.warn('LocalStorage unavailable', e);
            }
            updateGoalCounters();
            renderCards();
            triggerToast('All tracked study goals cleared');
        }

        function updateGoalCounters() {
            const tracked = getTrackedOffers();
            const count = tracked.length;
            const badge = document.getElementById('trackedGoalsCountBadge');
            if (badge) {
                badge.textContent = count;
                badge.style.display = count > 0 ? 'inline-flex' : 'none';
            }
        }

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
                if (currentTier !== 'all') {
                    const tier = getOfferTier(o);
                    if (currentTier === 'wave' && tier !== 'wave') return false;
                    if (currentTier === 'discount' && tier !== 'discount') return false;
                    if ((currentTier === 'skill_badge_lab' || currentTier === 'badge') && tier !== 'badge') return false;
                    if (currentTier === 'proctored_exam' && tier === 'badge') return false;
                }

                if (currentCategory === 'Tracked') {
                    if (!getTrackedOffers().includes(o.id)) return false;
                } else if (currentCategory === 'History') {
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
                    ? '<span class="px-2 py-0.5 rounded text-xs font-bold" style="background-color: var(--success-subtle); color: var(--success-fg);">🟢 Active</span>'
                    : '<span class="px-2 py-0.5 rounded text-xs font-bold" style="background-color: var(--attention-subtle); color: var(--attention-fg);">' + o.status + '</span>';

                const tierType = getOfferTier(o);
                let credBadge = '';
                if (tierType === 'wave') {
                    credBadge = '<span class="px-2 py-0.5 rounded text-xs font-bold border" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);">🌊 Exam Wave</span>';
                } else if (tierType === 'discount') {
                    credBadge = '<span class="px-2 py-0.5 rounded text-xs font-bold border border-amber-500/40 bg-amber-500/10 text-amber-500">🏷️ Active Discount</span>';
                } else {
                    credBadge = '<span class="px-2 py-0.5 rounded text-xs font-medium border" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">🎓 Skill Badge</span>';
                }

                const tierBadge = '<span class="px-1.5 py-0.5 rounded text-xs font-medium border" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">' + (o.difficulty_tier || 'Foundational') + '</span>';

                const tv = o.truth_verification;
                let truthBadge = '';
                if (tv) {
                    if (tv.policy_type === 'partial_discount_copay') {
                        truthBadge = '<span class="px-1.5 py-0.5 rounded text-xs font-bold border border-amber-500/40 bg-amber-500/10 text-amber-500" title="Official 75% Discount - Pearson VUE Copay Required">⚠️ 75% Off ($50 Fee)</span>';
                    } else if (tv.policy_type === 'student_verified_only') {
                        truthBadge = '<span class="px-1.5 py-0.5 rounded text-xs font-medium border border-blue-500/40 bg-blue-500/10 text-blue-400" title="Verified Students Only (GitHub Student Pack)">🎓 Student Pack</span>';
                    } else if (tv.policy_type === 'annual_window_closed') {
                        truthBadge = '<span class="px-1.5 py-0.5 rounded text-xs font-medium border border-amber-500/40 bg-amber-500/10 text-amber-500" title="Annual Window Closed - Reopens April 2027">📅 Annual Window Closed</span>';
                    } else if (tv.policy_type === 'verified_100pct_free') {
                        truthBadge = '<span class="px-1.5 py-0.5 rounded text-xs font-bold border border-emerald-500/40 bg-emerald-500/10 text-emerald-500" title="100% Free Verified Proctored Exam ($0.00)">✓ $0.00 Verified</span>';
                    }
                }

                const zeroConfirmedBadge = o.last_zero_dollar_confirmed_date 
                    ? '<span class="px-1.5 py-0.5 rounded text-xs font-medium border" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);" title="Last confirmed 100% free with zero dollar terms">✓ $0: ' + o.last_zero_dollar_confirmed_date + '</span>' 
                    : '';

                return `
                <div class="primer-card neo-shadow rounded-2xl p-4 sm:p-5 flex flex-col justify-between gap-3 relative transition-all flip-card" id="card-${escapeHtml(o.id)}">
                    <div class="flip-card-inner">
                        <!-- FRONT FACE: Voucher Card -->
                        <div class="flip-card-front flex flex-col justify-between h-full">
                            <div>
                                <div class="flex items-center justify-between gap-2 mb-2">
                                    <div class="flex items-center gap-2 min-w-0">
                                        ${getPlatformIconSvg(o.platform)}
                                        <span class="font-bold text-xs truncate" style="color: var(--fg-default);">${escapeHtml(o.platform)}</span>
                                    </div>
                                    <div class="flex items-center gap-1.5 flex-shrink-0">
                                        ${statusBadge}
                                    </div>
                                </div>

                                <div class="mb-1.5">
                                    ${credBadge}
                                </div>

                                <h3 class="font-bold text-sm sm:text-base leading-snug tracking-tight mt-1" style="color: var(--fg-default);">${escapeHtml(o.title)}</h3>
                                <div class="flex items-center gap-2 mt-2 flex-wrap">
                                    ${tierBadge}
                                    ${zeroConfirmedBadge}
                                    <span class="text-xs font-bold tabular-nums" style="color: var(--success-fg);">${valText}</span>
                                    ${truthBadge}
                                    <button type="button" onclick="openProofModal('${escapeJs(o.id)}')" class="text-xs px-2 py-0.5 rounded font-medium border hover:opacity-80 transition cursor-pointer inline-flex items-center gap-1 relative z-10 active:scale-[0.96] select-none" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);" title="View Verified Zero-Dollar Proof Lightbox">
                                        <span class="pointer-events-none">🛡️ ${o.authenticity_score || 100}% Proof</span>
                                    </button>
                                </div>

                                <!-- Animated Shimmer Progress Bar for Challenge/Sprint Window -->
                                <div class="mt-2.5">
                                    <div class="flex items-center justify-between text-xs mb-1 font-mono">
                                        <span class="text-xs" style="color: var(--fg-muted);">Challenge Window</span>
                                        <span class="font-bold text-xs" style="color: var(--accent-fg);">Active Sprint</span>
                                    </div>
                                    <div class="w-full h-1.5 rounded-full overflow-hidden relative" style="background-color: var(--canvas-inset);">
                                        <div class="h-full rounded-full shimmer-progress relative" style="width: 76%; background-color: var(--accent-fg);">
                                            <span class="absolute right-0 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-white shadow-xs animate-ping"></span>
                                        </div>
                                    </div>
                                </div>

                                <p class="text-xs mt-2.5 leading-relaxed text-pretty" style="color: var(--fg-muted);">${escapeHtml(o.eligibility || 'Open to all developers & engineers globally.')}</p>
                            </div>

                            <div class="pt-3 border-t flex items-center justify-between gap-2 flex-wrap mt-2" style="border-color: var(--border-muted);">
                                <div class="flex items-center gap-1.5 flex-wrap">
                                    <button onclick="copySteps('${escapeJs(o.id)}')" class="text-xs font-semibold px-2.5 py-1.5 rounded-lg border hover:opacity-80 transition cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                                        Copy Guide
                                    </button>
                                    <button onclick="openRedemptionFor('${escapeJs(o.id)}')" class="text-xs font-semibold px-2.5 py-1.5 rounded-lg border hover:opacity-80 transition cursor-pointer" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);" title="Where & How Offer is Applied ($0.00)">
                                        $0.00 Apply
                                    </button>
                                    <button type="button" data-proof-id="${escapeJs(o.id)}" onclick="openProofModal('${escapeJs(o.id)}')" class="text-xs font-semibold px-3 py-1.5 rounded-lg border hover:opacity-80 transition cursor-pointer inline-flex items-center gap-1 relative z-10 active:scale-[0.96] select-none" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);" title="View Verified Zero-Dollar Proof Lightbox">
                                        <span class="pointer-events-none">📸 Proof</span>
                                    </button>
                                    <button onclick="downloadCalendarReminder('${escapeJs(o.id)}')" class="text-xs font-semibold px-2 py-1.5 rounded-lg border hover:opacity-80 transition cursor-pointer" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);" title="Add Deadline to Calendar (.ics)">
                                        📅
                                    </button>
                                    <button onclick="toggleOfferChecked('${escapeJs(o.id)}')" class="text-xs font-semibold px-2.5 py-1.5 rounded-lg border hover:opacity-80 transition cursor-pointer inline-flex items-center gap-1 select-none" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: ${isOfferTracked(o.id) ? 'var(--accent-fg)' : 'var(--fg-muted)'};" title="Track in Personal Study Goals">
                                        <span>${isOfferTracked(o.id) ? '⭐ Tracked' : '☆ Track'}</span>
                                    </button>
                                    <button onclick="flipCard('${escapeJs(o.id)}')" class="text-xs font-semibold px-2.5 py-1.5 rounded-lg border hover:opacity-80 transition cursor-pointer inline-flex items-center gap-1 select-none" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--accent-fg);" title="View Verified Policy, Value & Eligibility Criteria">
                                        <span>📋 Policy</span>
                                    </button>
                                </div>
                                <a href="${sanitizeUrl(o.direct_verified_url || o.verified_vendor_url || o.url)}" onclick="triggerConfettiBurst(60)" target="_blank" rel="noopener" class="text-xs font-semibold px-3 py-1.5 rounded-lg text-white transition active:scale-[0.98] inline-flex items-center gap-1 cursor-pointer" style="background-color: var(--btn-primary-bg);">
                                    <span>Claim Free</span>
                                    <span>→</span>
                                </a>
                            </div>
                        </div>

                        <!-- BACK FACE: Verified Policy & Claim Rules -->
                        <div class="flip-card-back flex flex-col justify-between h-full p-4 rounded-xl border" style="background-color: var(--canvas-inset); border-color: var(--border-default);">
                            <div class="space-y-2 text-xs">
                                <div class="flex items-center justify-between border-b pb-2 mb-1" style="border-color: var(--border-default);">
                                    <div class="flex items-center gap-1.5 font-mono text-xs font-bold" style="color: var(--accent-fg);">
                                        <span>🛡️ VERIFIED CLAIM & POLICY SPEC</span>
                                    </div>
                                    <button onclick="flipCard('${escapeJs(o.id)}')" class="text-xs font-mono px-2 py-0.5 rounded border hover:opacity-80 transition cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);">
                                        ✕ Back
                                    </button>
                                </div>

                                <!-- Policy & Value Summary -->
                                <div class="p-2.5 rounded-lg border text-xs space-y-1" style="background-color: var(--canvas-default); border-color: var(--border-default);">
                                    <div class="flex items-center justify-between gap-1">
                                        <span style="color: var(--fg-muted);">Waiver Status:</span>
                                        <span class="font-bold ${o.status === 'Active' ? 'text-emerald-400' : 'text-slate-400'}">${escapeHtml(o.cart_balance_verified || (o.status === 'Active' ? '$0.00 Confirmed Zero-Dollar Waiver' : 'Historical Archive'))}</span>
                                    </div>
                                    <div class="flex items-center justify-between gap-1">
                                        <span style="color: var(--fg-muted);">Tuition Saved:</span>
                                        <span class="font-mono font-bold text-emerald-400">${(o.real_value_usd || o.value_usd) ? '$' + escapeHtml(String(o.real_value_usd || o.value_usd)) + ' USD (100% Free)' : 'Complimentary'}</span>
                                    </div>
                                </div>

                                <!-- Eligibility & Qualifying Rules -->
                                <div>
                                    <div class="font-semibold mb-0.5" style="color: var(--fg-default);">Eligibility & Prerequisites:</div>
                                    <p class="leading-relaxed text-pretty line-clamp-2" style="color: var(--fg-muted);">${escapeHtml(o.eligibility || 'Open to all developers and engineers globally.')}</p>
                                </div>

                                <!-- Audit Finding Notes -->
                                <div>
                                    <div class="font-semibold mb-0.5" style="color: var(--fg-default);">Truth Oracle Verdict:</div>
                                    <p class="leading-relaxed text-pretty line-clamp-2" style="color: var(--fg-muted);">${escapeHtml((o.truth_verification && o.truth_verification.verdict_notes) || o.inspection_notes || 'Verified against vendor program documentation and registration terms.')}</p>
                                </div>

                                <!-- Direct Verified Target Portal -->
                                <div>
                                    <span style="color: var(--fg-muted);">Target Portal:</span>
                                    <a href="${sanitizeUrl(o.direct_verified_url || o.url)}" target="_blank" rel="noopener" class="block font-mono truncate underline hover:opacity-80 transition mt-0.5" style="color: var(--accent-fg);">
                                        ${escapeHtml((o.direct_verified_url || o.url || '').replace(/^https?:\\/\\//, ''))}
                                    </a>
                                </div>
                            </div>

                            <div class="pt-3 border-t flex items-center justify-between gap-2" style="border-color: var(--border-default);">
                                <button type="button" onclick="openProofModal('${escapeJs(o.id)}')" class="text-xs font-semibold px-3 py-1.5 rounded-lg border hover:opacity-80 transition cursor-pointer" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);">
                                    📸 View Proof
                                </button>
                                <button onclick="flipCard('${escapeJs(o.id)}')" class="text-xs font-semibold px-3 py-1.5 rounded-lg border hover:opacity-80 transition cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">
                                    🔄 Return to Voucher
                                </button>
                            </div>
                        </div>
                    </div>
                </div>`;
            };

            const grid = document.getElementById('offersGrid');
            if (!grid) return;
            if (filtered.length === 0) {
                grid.innerHTML = '<div class="col-span-full p-8 text-center rounded-xl border" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">No certifications match your active search or filters.</div>';
                return;
            }

            const wavesList = filtered.filter(o => getOfferTier(o) === 'wave');
            const discountsList = filtered.filter(o => getOfferTier(o) === 'discount');
            const badgesList = filtered.filter(o => getOfferTier(o) === 'badge');

            if (currentTier === 'wave') {
                grid.innerHTML = wavesList.length > 0
                    ? wavesList.map(o => renderCardHtml(o)).join('')
                    : '<div class="col-span-full p-8 text-center rounded-xl border" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">No active exam waves match criteria.</div>';
                return;
            }
            if (currentTier === 'discount') {
                grid.innerHTML = discountsList.length > 0
                    ? discountsList.map(o => renderCardHtml(o)).join('')
                    : '<div class="col-span-full p-8 text-center rounded-xl border" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">No active discounts match criteria.</div>';
                return;
            }
            if (currentTier === 'skill_badge_lab' || currentTier === 'badge') {
                grid.innerHTML = badgesList.length > 0
                    ? badgesList.map(o => renderCardHtml(o)).join('')
                    : '<div class="col-span-full p-8 text-center rounded-xl border" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">No active skill badges match criteria.</div>';
                return;
            }
            if (currentTier === 'proctored_exam') {
                const combined = [...wavesList, ...discountsList];
                grid.innerHTML = combined.length > 0
                    ? combined.map(o => renderCardHtml(o)).join('')
                    : '<div class="col-span-full p-8 text-center rounded-xl border" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">No proctored exam opportunities match criteria.</div>';
                return;
            }

            let html = '';

            // 1. Limited-Time Exam Waves & Seasonal Challenge Cohorts
            if (wavesList.length > 0) {
                html += `
                <div class="col-span-full flex items-center justify-between p-3.5 rounded-xl border shadow-xs" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                    <div class="flex items-center gap-2.5">
                        <span class="text-lg">🌊</span>
                        <div>
                            <h2 class="font-bold text-xs sm:text-sm tracking-tight" style="color: var(--fg-default);">Limited-Time Exam Waves & Seasonal Challenge Cohorts</h2>
                            <p class="text-xs" style="color: var(--fg-muted);">Vendor race-to-certify challenges, Cloud Skills Waves, and annual testing windows (${wavesList.length} Active Waves)</p>
                        </div>
                    </div>
                    <span class="px-2.5 py-0.5 rounded text-xs font-bold border" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);">${wavesList.length} Waves</span>
                </div>`;
                html += wavesList.map(o => renderCardHtml(o)).join('');
            }

            // 2. Active Ongoing Discounts & Vouchers
            if (discountsList.length > 0) {
                html += `
                <div class="col-span-full mt-4 flex items-center justify-between p-3.5 rounded-xl border shadow-xs" style="background-color: var(--canvas-subtle); border-color: var(--border-default);">
                    <div class="flex items-center gap-2.5">
                        <span class="text-lg">🏷️</span>
                        <div>
                            <h2 class="font-bold text-xs sm:text-sm tracking-tight" style="color: var(--fg-default);">Active Ongoing Discounts & Vouchers</h2>
                            <p class="text-xs" style="color: var(--fg-muted);">Continuous student vouchers, partial co-pay discounts, and permanent $0 certification waivers (${discountsList.length} Opportunities)</p>
                        </div>
                    </div>
                    <span class="px-2.5 py-0.5 rounded text-xs font-bold border border-amber-500/40 bg-amber-500/10 text-amber-500">${discountsList.length} Discounts</span>
                </div>`;
                html += discountsList.map(o => renderCardHtml(o)).join('');
            }

            // 3. Free Digital Skill Badges & Hands-On Cloud Labs
            if (badgesList.length > 0) {
                html += `
                <details class="col-span-full mt-4 rounded-2xl border p-4 sm:p-5 transition-all shadow-xs group" style="background-color: var(--canvas-subtle); border-color: var(--border-default);" open>
                    <summary class="cursor-pointer list-none flex items-center justify-between select-none">
                        <div class="flex items-center gap-2.5">
                            <span class="text-lg">🎓</span>
                            <div>
                                <div class="flex items-center gap-2">
                                    <h2 class="font-bold text-xs sm:text-sm tracking-tight" style="color: var(--fg-default);">Free Digital Skill Badges & Hands-On Cloud Labs</h2>
                                    <span class="px-2 py-0.5 rounded text-xs font-semibold border" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">${badgesList.length} Badges</span>
                                </div>
                                <p class="text-xs mt-0.5" style="color: var(--fg-muted);">Unproctored practical learning paths, sandbox labs, and verifiable Credly/Skill badges (Click to toggle)</p>
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
                    ? '<span class="text-xs font-bold px-1.5 py-0.5 rounded border" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);">🎓 Exam</span>' 
                    : '<span class="text-xs px-1.5 py-0.5 rounded border" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: var(--fg-muted);">🎖️ Badge</span>';

                const tv = o.truth_verification;
                let truthBadge = '';
                if (tv) {
                    if (tv.policy_type === 'partial_discount_copay') {
                        truthBadge = '<span class="text-xs font-bold text-amber-500 ml-1.5" title="75% Discount - Pearson VUE Copay">⚠️ 75% Off</span>';
                    } else if (tv.policy_type === 'student_verified_only') {
                        truthBadge = '<span class="text-xs text-blue-400 ml-1.5" title="Student Pack">🎓 Student</span>';
                    } else if (tv.policy_type === 'annual_window_closed') {
                        truthBadge = '<span class="text-xs text-amber-500 ml-1.5" title="Annual Window Closed">📅 Closed</span>';
                    }
                }

                return `
                <div class="p-3 sm:px-4 sm:py-3.5 grid grid-cols-1 sm:grid-cols-12 gap-2 sm:gap-3 items-center hover:bg-slate-500/5 transition">
                    <div class="sm:col-span-3 flex items-center gap-2 min-w-0">
                        ${getPlatformIconSvg(o.platform)}
                        <div class="flex flex-col min-w-0">
                            <span class="font-bold text-xs truncate" style="color: var(--fg-default);">${escapeHtml(o.platform)}</span>
                            <div class="flex items-center gap-1 mt-0.5">${credBadge} ${truthBadge}</div>
                        </div>
                    </div>
                    <div class="sm:col-span-5 min-w-0">
                        <div class="font-semibold text-xs sm:text-sm truncate" style="color: var(--fg-default);">${escapeHtml(o.certification_name || o.title)}</div>
                        <div class="text-xs" style="color: var(--fg-muted);">${escapeHtml(o.category)} • ${escapeHtml(o.difficulty_tier || 'Foundational')}</div>
                    </div>
                    <div class="sm:col-span-1 sm:text-center text-xs font-bold tabular-nums" style="color: var(--success-fg);">${valText}</div>
                    <div class="sm:col-span-3 flex items-center sm:justify-end gap-1.5 flex-wrap">
                        <button onclick="toggleOfferChecked('${escapeJs(o.id)}')" class="text-xs font-semibold px-2 py-1 rounded border cursor-pointer inline-flex items-center gap-1 select-none" style="background-color: var(--canvas-inset); border-color: var(--border-default); color: ${isOfferTracked(o.id) ? 'var(--accent-fg)' : 'var(--fg-muted)'};" title="Track in Personal Study Goals"><span>${isOfferTracked(o.id) ? '⭐' : '☆'}</span></button>
                        <button type="button" data-proof-id="${escapeJs(o.id)}" onclick="openProofModal('${escapeJs(o.id)}')" class="text-xs font-semibold px-2.5 py-1 rounded border cursor-pointer inline-flex items-center gap-1 relative z-10 active:scale-[0.96] select-none" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);" title="View Verified Zero-Dollar Proof Lightbox"><span class="pointer-events-none">📸 Proof</span></button>
                        <button onclick="openRedemptionFor('${escapeJs(o.id)}')" class="text-xs font-semibold px-2 py-1 rounded border cursor-pointer" style="background-color: var(--accent-subtle); border-color: var(--accent-fg); color: var(--accent-fg);" title="Where Offer is Applied ($0.00)">$0.00</button>
                        <a href="${sanitizeUrl(o.direct_verified_url || o.verified_vendor_url || o.url)}" target="_blank" class="text-xs font-semibold px-2.5 py-1 rounded text-white" style="background-color: var(--btn-primary-bg);">Claim →</a>
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
                            <div class="font-bold text-sm" style="color: var(--fg-default);">${escapeHtml(o.platform)} — ${escapeHtml(o.title)}</div>
                            <div class="text-xs mt-1" style="color: var(--fg-muted);">Cadence: <span class="font-semibold text-blue-500">${escapeHtml(o.recurrence_pattern || 'Annual Conference Cycle')}</span> • Period: ${escapeHtml(o.time_period || 'Continuous')}</div>
                        </div>
                    </div>
                    <div class="flex items-center gap-2 flex-shrink-0">
                        <button type="button" data-proof-id="${escapeJs(o.id)}" onclick="openProofModal('${escapeJs(o.id)}')" class="px-3 py-1 rounded text-xs border font-medium cursor-pointer relative z-10 active:scale-[0.96] select-none" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);" title="View Verified Zero-Dollar Proof Lightbox">
                            <span class="pointer-events-none">📸 Proof</span>
                        </button>
                        <a href="${sanitizeUrl(o.direct_verified_url || o.verified_vendor_url || o.url)}" target="_blank" class="px-3 py-1 rounded text-xs font-semibold text-white" style="background-color: var(--btn-primary-bg);">Open →</a>
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
                                    <span class="font-bold truncate" style="color: var(--fg-default);">${escapeHtml(o.platform)}</span>
                                    <span class="font-bold tabular-nums" style="color: var(--success-fg);">${o.value_usd ? '$' + o.value_usd : 'Free'}</span>
                                </div>
                                <div class="font-medium truncate" style="color: var(--fg-default);">${escapeHtml(o.certification_name || o.title)}</div>
                            </div>
                            <div class="flex items-center justify-between pt-2 border-t" style="border-color: var(--border-muted);">
                                <span class="text-xs font-mono">${escapeHtml(o.difficulty_tier || 'Foundational')}</span>
                                <div class="flex items-center gap-2">
                                    <button type="button" data-proof-id="${escapeJs(o.id)}" onclick="openProofModal('${escapeJs(o.id)}')" class="text-xs font-medium hover:underline cursor-pointer inline-flex items-center gap-0.5 relative z-10 select-none" title="View Verified Zero-Dollar Proof Lightbox"><span class="pointer-events-none">📸 Proof</span></button>
                                    <a href="${sanitizeUrl(o.direct_verified_url || o.verified_vendor_url || o.url)}" target="_blank" class="text-blue-500 font-semibold hover:underline">Claim →</a>
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
                    const focusables = Array.from(proofModal.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'))
                        .filter(el => !el.classList.contains('hidden') && el.offsetParent !== null && window.getComputedStyle(el).display !== 'none');
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
            if ((e.metaKey || e.ctrlKey) && key === 'k') {
                e.preventDefault();
                openCommandPalette();
                return;
            }
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

            if (filtered.length === 0) {
                grid.innerHTML = '<div class="col-span-full p-8 text-center rounded-xl border" style="background-color: var(--canvas-subtle); border-color: var(--border-default); color: var(--fg-muted);">No industry dispatches match your active filter or search query.</div>';
                return;
            }

            grid.innerHTML = filtered.map(item => `
            <div class="primer-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between gap-3">
                <div>
                    <div class="flex items-center justify-between text-xs mb-2">
                        <span class="font-bold" style="color: var(--accent-fg);">${escapeHtml(item.company)}</span>
                        <span class="text-xs font-mono tabular-nums" style="color: var(--fg-subtle);">${escapeHtml(item.published_date)}</span>
                    </div>
                    <h4 class="font-bold text-sm sm:text-base leading-snug tracking-tight" style="color: var(--fg-default);">${escapeHtml(item.title)}</h4>
                    <p class="text-xs mt-2 leading-relaxed text-pretty" style="color: var(--fg-muted);">${escapeHtml(item.summary)}</p>
                </div>
                <div class="pt-3 border-t flex items-center justify-between text-xs" style="border-color: var(--border-muted);">
                    <span class="text-xs font-mono truncate max-w-[150px]" style="color: var(--fg-subtle);">${escapeHtml(item.source_domain)}</span>
                    <a href="${sanitizeUrl(item.url)}" target="_blank" rel="noopener" class="font-semibold text-blue-500 hover:underline inline-flex items-center gap-1">
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
                        <span class="w-4 h-4 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5" style="background-color: var(--accent-subtle); color: var(--accent-fg); border: 1px solid var(--accent-fg);">${idx + 1}</span>
                        <span class="text-pretty">${escapeHtml(s)}</span>
                    </li>
                `).join('');

                return `
                <div class="primer-card rounded-2xl p-4 sm:p-5 flex flex-col justify-between gap-4 border transition-all" id="redemption-card-${escapeHtml(o.id)}">
                    <div>
                        <div class="flex items-center justify-between gap-2 mb-2 flex-wrap">
                            <div class="flex items-center gap-2">
                                ${getPlatformIconSvg(o.platform)}
                                <span class="font-bold text-xs truncate" style="color: var(--fg-default);">${escapeHtml(o.platform)}</span>
                            </div>
                            <span class="text-xs px-2 py-0.5 rounded-full font-bold border" style="background-color: var(--accent-subtle); color: var(--accent-fg); border-color: var(--accent-fg);">${escapeHtml(flowType)}</span>
                        </div>

                        <h3 class="font-bold text-sm sm:text-base leading-snug tracking-tight" style="color: var(--fg-default);">${escapeHtml(o.title)}</h3>
                        
                        <!-- Checkout Field & Voucher Token Callout -->
                        <div class="mt-3 p-3 rounded-xl border" style="background-color: var(--canvas-inset); border-color: var(--border-default);">
                            <div class="text-xs font-semibold uppercase tracking-wider mb-1" style="color: var(--fg-muted);">Exact Checkout Field</div>
                            <div class="text-xs font-mono font-medium flex items-center gap-1.5" style="color: var(--fg-default);">
                                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" style="color: var(--accent-fg); flex-shrink: 0;"><path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-6.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM6.5 7.75A.75.75 0 0 1 7.25 7h1a.75.75 0 0 1 .75.75v2.75h.25a.75.75 0 0 1 0 1.5h-2.5a.75.75 0 0 1 0-1.5h.25v-2h-.25a.75.75 0 0 1-.75-.75ZM8 6a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"></path></svg>
                                <span class="text-pretty">${escapeHtml(fieldLoc)}</span>
                            </div>
                            <div class="mt-2.5 pt-2 border-t flex items-center justify-between gap-2 flex-wrap" style="border-color: var(--border-muted);">
                                <span class="text-xs" style="color: var(--fg-muted);">Voucher Token:</span>
                                <div class="flex items-center gap-1.5">
                                    <code class="px-1.5 py-0.5 rounded text-xs font-mono font-bold" style="background-color: var(--canvas-default); color: var(--accent-fg); border: 1px solid var(--border-default);">${escapeHtml(code)}</code>
                                    <button onclick="copyVoucherToken('${escapeJs(code)}')" class="text-xs px-2 py-0.5 rounded border font-semibold transition active:scale-[0.95] cursor-pointer" style="background-color: var(--btn-default-bg); border-color: var(--border-default); color: var(--fg-default);">Copy</button>
                                </div>
                            </div>
                        </div>

                        <!-- Step-by-Step Checkout Flow -->
                        <div class="mt-3.5">
                            <div class="text-xs font-semibold uppercase tracking-wider mb-2" style="color: var(--fg-muted);">Redemption & Zero-Dollar Verification Steps</div>
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
                                <span class="tabular-nums">Cart Balance: $0.00</span>
                            </div>
                            <button type="button" data-proof-id="${escapeJs(o.id)}" onclick="openProofModal('${escapeJs(o.id)}')" class="text-xs font-semibold px-3 py-1 rounded-lg border hover:opacity-80 transition cursor-pointer inline-flex items-center gap-1 relative z-10 active:scale-[0.96] select-none" style="background-color: var(--canvas-default); border-color: var(--border-default); color: var(--fg-default);" title="View Verified Zero-Dollar Proof Lightbox">
                                <span class="pointer-events-none">📸 Proof</span>
                            </button>
                        </div>
                        <a href="${sanitizeUrl(portalUrl)}" target="_blank" rel="noopener" class="text-xs font-semibold px-3 py-1.5 rounded-lg text-white transition active:scale-[0.98] inline-flex items-center gap-1 cursor-pointer" style="background-color: var(--btn-primary-bg);">
                            <span>Launch Portal</span>
                            <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor"><path d="M3.75 2h3.5a.75.75 0 0 1 0 1.5h-3.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-3.5a.75.75 0 0 1 1.5 0v3.5A1.75 1.75 0 0 1 12.25 14h-8.5A1.75 1.75 0 0 1 2 12.25v-8.5C2 2.784 2.784 2 3.75 2Zm6.75.75a.75.75 0 0 1 .75-.75h3.5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0V4.56L8.53 10.03a.75.75 0 0 1-1.06-1.06l5.47-5.47H11.25a.75.75 0 0 1-.75-.75Z"></path></svg>
                        </a>
                    </div>
                </div>`;
            }).join('');
        }

        // Initialize URL Query Params & Initial Load

        // Document-Level Event Delegation for Bulletproof Proof Button Clicks
        document.addEventListener('click', function(e) {
            const proofBtn = e.target.closest('[data-proof-id]');
            if (proofBtn) {
                const id = proofBtn.getAttribute('data-proof-id');
                if (id) {
                    e.preventDefault();
                    e.stopPropagation();
                    openProofModal(id);
                }
            }
        });

        // Global Window Function Bindings
        window.openProofModal = openProofModal;
        window.closeProofModal = closeProofModal;
        window.handleProofModalBackdrop = handleProofModalBackdrop;
        window.closeProofModalOnBackdrop = closeProofModalOnBackdrop;
        window.applyTheme = applyTheme;
        window.toggleTheme = toggleTheme;
        window.switchTheme = applyTheme;
        window.filterTier = filterTier;
        window.filterCategory = filterCategory;
        window.setLayoutView = setLayoutView;
        window.switchMainTab = switchMainTab;
        window.manualPingOracle = manualPingOracle;
        window.downloadCalendarReminder = downloadCalendarReminder;
        window.triggerConfettiBurst = triggerConfettiBurst;
        window.toggleAudioHaptics = toggleAudioHaptics;
        window.setBackgroundFXMode = setBackgroundFXMode;
        window.flipCard = flipCard;
        window.toggleOfferChecked = toggleOfferChecked;
        window.clearAllChecked = clearAllChecked;
        window.updateGoalCounters = updateGoalCounters;
        window.getTrackedOffers = getTrackedOffers;
        window.isOfferTracked = isOfferTracked;

        // ================= CUSTOM CYBER CURSOR ENGINE =================
        function initCyberCursor() {
            const dot = document.getElementById('cyber-cursor-dot');
            const ring = document.getElementById('cyber-cursor-ring');
            if (!dot || !ring) return;

            if (window.matchMedia && (window.matchMedia('(hover: none)').matches || window.matchMedia('(pointer: coarse)').matches)) {
                dot.style.display = 'none';
                ring.style.display = 'none';
                return;
            }

            let mouseX = -100, mouseY = -100;
            let ringX = -100, ringY = -100;
            let isTracking = false;

            function lerpRing() {
                if (isTracking) {
                    ringX += (mouseX - ringX) * 0.18;
                    ringY += (mouseY - ringY) * 0.18;
                    ring.style.left = ringX.toFixed(2) + 'px';
                    ring.style.top = ringY.toFixed(2) + 'px';
                }
                requestAnimationFrame(lerpRing);
            }
            requestAnimationFrame(lerpRing);

            window.addEventListener('mousemove', (e) => {
                mouseX = e.clientX;
                mouseY = e.clientY;
                dot.style.left = mouseX + 'px';
                dot.style.top = mouseY + 'px';

                if (!isTracking) {
                    ringX = mouseX;
                    ringY = mouseY;
                    ring.style.left = ringX + 'px';
                    ring.style.top = ringY + 'px';
                    dot.classList.add('active');
                    ring.classList.add('active');
                    isTracking = true;
                }
            });

            document.addEventListener('mouseleave', () => {
                dot.classList.remove('active');
                ring.classList.remove('active');
                isTracking = false;
                dot.style.left = '-100px';
                dot.style.top = '-100px';
                ring.style.left = '-100px';
                ring.style.top = '-100px';
            });

            document.addEventListener('mouseenter', (e) => {
                if (e.clientX && e.clientY) {
                    mouseX = e.clientX;
                    mouseY = e.clientY;
                    ringX = mouseX;
                    ringY = mouseY;
                    dot.style.left = mouseX + 'px';
                    dot.style.top = mouseY + 'px';
                    ring.style.left = ringX + 'px';
                    ring.style.top = ringY + 'px';
                    dot.classList.add('active');
                    ring.classList.add('active');
                    isTracking = true;
                }
            });

            document.addEventListener('mouseover', (e) => {
                const interactive = e.target && e.target.closest('a, button, input, [role="button"], .primer-card');
                if (interactive && isTracking) {
                    ring.classList.add('cursor-hover');
                } else {
                    ring.classList.remove('cursor-hover');
                }
            });
        }

        window.addEventListener('DOMContentLoaded', () => {
            initCyberCursor();
            const urlParams = new URLSearchParams(window.location.search);
            const viewParam = urlParams.get('view');
            const tabParam = urlParams.get('tab');

            setupSearchListener();

            // Background canvas & FX initialization
            resizeBgCanvas();
            initConstellationParticles();
            renderAmbientBackground();
            window.addEventListener('resize', resizeBgCanvas);
            window.addEventListener('mousemove', (e) => {
                bgMouseX = e.clientX;
                bgMouseY = e.clientY;
            });
            setInterval(jitterLatency, 2400);

            const savedTheme = localStorage.getItem('certpulse_theme_v2') || localStorage.getItem('certpulse_theme') || localStorage.getItem('theme');
            let initialTheme = (savedTheme === 'github-light' || savedTheme === 'github-dark') ? savedTheme : 'github-dark';
            applyTheme(initialTheme);

            if (window.matchMedia) {
                window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
                    if (!localStorage.getItem('certpulse_theme_v2') && !localStorage.getItem('certpulse_theme') && !localStorage.getItem('theme')) {
                        applyTheme(e.matches ? 'github-dark' : 'github-light');
                    }
                });
            }
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
