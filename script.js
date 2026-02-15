// Singapore Budget Speeches - Storytelling Visualization
// Inspired by Pudding.cool's democracy piece

let vizData = null;
let storyData = null;
let wordTrendsData = null;
let svg = null;
let dots = null;
let currentSection = null;
let filteredParagraphs = null;
let yearPositions = {};

// Cached DOM elements (initialized after DOMContentLoaded)
let domElements = {
    currentEra: null,
    currentContext: null,
    progressFill: null,
    timelineViz: null,
    scrollSections: null,
    hoverPanel: null,
    quoteModal: null,
    exploreSection: null
};

// Initialize cached DOM elements
function initDomElements() {
    domElements.currentEra = document.querySelector('.current-era');
    domElements.currentContext = document.querySelector('.current-context');
    domElements.progressFill = document.querySelector('.progress-fill');
    domElements.timelineViz = document.getElementById('timeline-viz');
    domElements.scrollSections = document.getElementById('scroll-sections');
    domElements.hoverPanel = document.getElementById('hover-panel');
    domElements.quoteModal = document.getElementById('quote-modal');
    domElements.exploreSection = document.querySelector('[data-step="explore"]');
}

// Responsive sizing helper
function getResponsiveConfig() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    const isMobile = width <= 768;
    const isSmallMobile = width <= 480;
    const isLandscape = width > height;

    return {
        dotSize: isSmallMobile ? 2.2 : (isMobile ? 2.8 : 3.3),
        dotGap: isSmallMobile ? 0.3 : (isMobile ? 0.4 : 0.6),
        marginTop: isSmallMobile ? 10 : (isMobile ? 15 : 200),
        marginRight: isMobile ? 10 : 25,
        marginBottom: isSmallMobile ? 18 : (isMobile ? 20 : 20),
        marginLeft: isMobile ? 10 : 25,
        hideAnnotations: isMobile,
        maxCols: isSmallMobile ? 4 : (isMobile ? 5 : 6),
        isMobile: isMobile,
        isSmallMobile: isSmallMobile,
        hideSvgLegend: isMobile, // Hide SVG legend on mobile, use CSS legend
        fontSize: {
            year: isSmallMobile ? '8px' : (isMobile ? '9px' : '13px'),
            legend: isSmallMobile ? '8px' : (isMobile ? '9px' : '10.5px'),
            event: isSmallMobile ? '7px' : (isMobile ? '8px' : '9px')
        }
    };
}

// Get current DOT_SIZE (for hover detection)
function getDotSize() {
    return getResponsiveConfig().dotSize;
}


// Prevent browser from restoring scroll position
if ('scrollRestoration' in history) {
    history.scrollRestoration = 'manual';
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Cache DOM elements first
    initDomElements();

    // Scroll to top on page load
    window.scrollTo(0, 0);

    // Also scroll after a brief delay to override any browser restoration
    setTimeout(() => window.scrollTo(0, 0), 100);

    try {
        const [vizResponse, storyResponse, trendsResponse] = await Promise.all([
            fetch('viz_data.json'),
            fetch('curated_story.json'),
            fetch('word_trends.json')
        ]);

        vizData = await vizResponse.json();
        storyData = await storyResponse.json();
        wordTrendsData = await trendsResponse.json();

        // Only show promises and obligations, not grey neutral paragraphs
        filteredParagraphs = vizData.paragraphs.filter(p =>
            p.primary_value && p.primary_value !== 'none'
        );

        generateStorySections();
        initVisualization();
        setupScrollTriggers();
        setupModal();
        // Native D3 event handlers on dots handle hover/click

    } catch (error) {
        console.error('Error:', error);
    }
});

// Generate story sections from curated data
function generateStorySections() {
    const container = domElements.scrollSections;

    storyData.sections.forEach((section, index) => {
        const el = document.createElement('section');
        el.className = 'step';
        el.dataset.step = section.id;
        el.dataset.yearStart = section.year_range[0];
        el.dataset.yearEnd = section.year_range[1];

        let content = '';

        if (section.type === 'word_trends_intro') {
            // Introduction to word trends
            content = `
                <div class="step-content trends-intro-content">
                    ${section.era_label ? `<span class="era-badge">${section.era_label}</span>` : ''}
                    <h3>${section.title}</h3>
                    <p class="setup">${section.setup}</p>
                </div>
            `;
        } else if (section.type === 'stat_highlight') {
            // Big stat highlight with bar chart
            const stats = storyData.stats;
            content = `
                <div class="step-content stat-highlight-content">
                    ${section.era_label ? `<span class="era-badge">${section.era_label}</span>` : ''}
                    ${section.title ? `<h3>${section.title}</h3>` : ''}
                    <p class="setup">${section.setup}</p>
                    <div class="word-change-viz">
                        <div class="word-bars">
                            <div class="word-bar-row">
                                <span class="bar-label">${stats.then.year}</span>
                                <div class="bar-container">
                                    <div class="bar bar-then" style="width: 4%"></div>
                                    <span class="bar-value">${stats.headline.then_rate}</span>
                                </div>
                            </div>
                            <div class="word-bar-row">
                                <span class="bar-label">${stats.now.year}</span>
                                <div class="bar-container">
                                    <div class="bar bar-now" style="width: 100%"></div>
                                    <span class="bar-value">${stats.headline.now_rate}</span>
                                </div>
                            </div>
                        </div>
                        <div class="word-change-multiplier">${stats.headline.multiplier} increase</div>
                        <div class="word-change-unit">(mentions ${stats.headline.unit})</div>
                    </div>
                    ${section.reflection ? `<p class="reflection">${section.reflection}</p>` : ''}
                </div>
            `;
        } else if (section.type === 'pm_era_chart') {
            // PM Era chart showing promises vs demands as stacked bars
            const pmData = section.pm_data || [];

            content = `
                <div class="step-content pm-era-content">
                    ${section.era_label ? `<span class="era-badge">${section.era_label}</span>` : ''}
                    ${section.title ? `<h3>${section.title}</h3>` : ''}
                    ${section.setup ? `<p class="setup">${section.setup}</p>` : ''}
                    <div class="pm-era-chart">
                        ${pmData.map((d, i) => {
                            const total = d.promises + d.demands;
                            const promisePct = (d.promises / total) * 100;
                            const demandPct = (d.demands / total) * 100;
                            return `
                            <div class="pm-era-row">
                                <div class="pm-era-label">
                                    <span class="pm-name">${d.pm}</span>
                                    <span class="pm-years">${d.years}</span>
                                </div>
                                <div class="pm-era-bar-container stacked">
                                    <div class="pm-era-bar-segment promises" style="width: ${promisePct}%">
                                        <span class="segment-label">${d.promises}</span>
                                    </div>
                                    <div class="pm-era-bar-segment demands" style="width: ${demandPct}%">
                                        <span class="segment-label">${d.demands}</span>
                                    </div>
                                </div>
                            </div>
                        `}).join('')}
                    </div>
                    <div class="pm-era-legend">
                        <div class="pm-era-legend-item">
                            <span class="legend-color promises"></span>
                            <span>Promises</span>
                        </div>
                        <div class="pm-era-legend-item">
                            <span class="legend-color demands"></span>
                            <span>Demands</span>
                        </div>
                    </div>
                    ${section.reflection ? `<p class="reflection">${section.reflection}</p>` : ''}
                </div>
            `;
        } else if (section.type === 'decade_chart') {
            // Decade chart showing promises vs demands as stacked bars
            const decadeData = section.decade_data || [];

            content = `
                <div class="step-content decade-era-content">
                    ${section.era_label ? `<span class="era-badge">${section.era_label}</span>` : ''}
                    ${section.title ? `<h3>${section.title}</h3>` : ''}
                    ${section.setup ? `<p class="setup">${section.setup}</p>` : ''}
                    <div class="decade-chart">
                        ${decadeData.map((d, i) => {
                            const total = d.promises + d.demands;
                            const promisePct = (d.promises / total) * 100;
                            const demandPct = (d.demands / total) * 100;
                            return `
                            <div class="decade-row">
                                <div class="decade-label">
                                    <span class="decade-name">${d.decade}</span>
                                </div>
                                <div class="decade-bar-container stacked">
                                    <div class="decade-bar-segment promises" style="width: ${promisePct}%">
                                        <span class="segment-label">${d.promises}</span>
                                    </div>
                                    <div class="decade-bar-segment demands" style="width: ${demandPct}%">
                                        <span class="segment-label">${d.demands}</span>
                                    </div>
                                </div>
                            </div>
                        `}).join('')}
                    </div>
                    <div class="decade-legend">
                        <div class="decade-legend-item">
                            <span class="legend-color promises"></span>
                            <span>Promises</span>
                        </div>
                        <div class="decade-legend-item">
                            <span class="legend-color demands"></span>
                            <span>Demands</span>
                        </div>
                    </div>
                    ${section.reflection ? `<p class="reflection">${section.reflection}</p>` : ''}
                </div>
            `;
        } else if (section.type === 'word_trends') {
            // Word trends with sparklines
            const trends = section.trend_type === 'rising' ? wordTrendsData.rising : wordTrendsData.declining;
            const color = section.trend_type === 'rising' ? '#D35F5F' : '#3D5A80';

            content = `
                <div class="step-content trends-content ${section.trend_type}">
                    <span class="era-badge">${section.era_label}</span>
                    <h3>${section.title}</h3>
                    ${section.setup ? `<p class="setup">${section.setup}</p>` : ''}
                    <div class="sparkline-grid" data-trend-type="${section.trend_type}">
                        ${trends.slice(0, 12).map(w => `
                            <div class="sparkline-item">
                                <div class="sparkline-word">${w.word}</div>
                                <svg class="sparkline" data-values="${w.timeseries.map(d => d.per_10k).join(',')}" data-color="${color}"></svg>
                                <div class="sparkline-change ${section.trend_type}">${w.change > 0 ? '+' : ''}${w.change}</div>
                                <div class="sparkline-rate">past 10 yrs: ${w.recent_per_10k.toFixed(1)}</div>
                            </div>
                        `).join('')}
                    </div>
                    ${section.reflection ? `<p class="reflection">${section.reflection}</p>` : ''}
                </div>
            `;
        } else if (section.type === 'final') {
            // Final section
            content = `
                <div class="step-content final-content">
                    <h3>${section.title}</h3>
                    <div class="final-text">${section.reflection.split('\n\n').map(p => `<p>${p}</p>`).join('')}</div>
                </div>
            `;
        } else if (section.type === 'explore') {
            // Final explore section - scrolls away to reveal interactive chart
            el.classList.add('step-explore');
            // Use different text for mobile (click) vs desktop (hover)
            const isMobileDevice = window.innerWidth <= 768;
            const exploreText = isMobileDevice
                ? 'Tap any square to see the paragraph it represents.'
                : section.reflection;
            content = `
                <div class="step-content explore-content">
                    <span class="era-badge">${section.era_label}</span>
                    <h3>${section.title}</h3>
                    <div class="explore-text">${exploreText.split('\n\n').map(p => `<p>${p}</p>`).join('')}</div>
                    <div class="explore-hint">
                        <span class="hint-icon">↓</span>
                        <span>Keep scrolling, then hover over any square</span>
                    </div>
                </div>
            `;
        } else if (section.type === 'fullscreen') {
            // Full-screen interstitial - no card, just content
            el.classList.add('step-fullscreen');
            content = `
                <div class="fullscreen-content">
                    ${section.title ? `<h2 class="fullscreen-title">${section.title}</h2>` : ''}
                    ${section.setup ? `<div class="fullscreen-text">${section.setup.split('\n\n').map(p => `<p>${p}</p>`).join('')}</div>` : ''}
                </div>
            `;
        } else if (section.type === 'fm_table') {
            // FM fingerprints table
            const fmData = section.fm_words || [];
            content = `
                <div class="step-content fm-table-content">
                    ${section.era_label ? `<span class="era-badge">${section.era_label}</span>` : ''}
                    ${section.title ? `<h3>${section.title}</h3>` : ''}
                    ${section.setup ? `<p class="setup">${section.setup}</p>` : ''}
                    <table class="fm-table">
                        <thead>
                            <tr><th>Era</th><th>Finance Minister</th><th>Pet Words</th></tr>
                        </thead>
                        <tbody>
                            ${fmData.map(d => `
                                <tr>
                                    <td class="fm-era">${d.era}</td>
                                    <td class="fm-name">${d.fm}</td>
                                    <td class="fm-words">${d.words}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                    ${section.reflection ? `<p class="reflection">${section.reflection}</p>` : ''}
                </div>
            `;
        } else if (section.type === 'persistent_words_chart') {
            // Persistent words heatmap-style table
            const wordData = section.word_data || [];
            const decades = section.decades || ['60s', '70s', '80s', '90s', '00s', '10s', '20s'];

            content = `
                <div class="step-content persistent-words-content">
                    ${section.era_label ? `<span class="era-badge">${section.era_label}</span>` : ''}
                    ${section.title ? `<h3>${section.title}</h3>` : ''}
                    ${section.setup ? `<p class="setup">${section.setup}</p>` : ''}
                    <table class="persistent-words-table">
                        <thead>
                            <tr>
                                <th></th>
                                ${decades.map(d => `<th>${d}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${wordData.map(w => `
                                <tr>
                                    <td class="word-label">${w.word}</td>
                                    ${w.rates.map(r => {
                                        const intensity = Math.min(r / 20, 1); // normalize to 0-1
                                        const bg = `rgba(61, 90, 128, ${intensity * 0.7 + 0.1})`;
                                        const color = intensity > 0.4 ? 'white' : 'var(--charcoal)';
                                        return `<td class="rate-cell" style="background:${bg};color:${color}">${r.toFixed(1)}</td>`;
                                    }).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                    <p class="table-note">Mentions per 10,000 words</p>
                    ${section.reflection ? `<p class="reflection">${section.reflection}</p>` : ''}
                </div>
            `;
        } else if (section.type === 'prose') {
            // Regular article text - no card, just body text
            el.classList.add('step-prose');
            content = `
                <div class="prose-content">
                    ${section.setup ? `<div class="prose-text">${section.setup.split('\n\n').map(p => `<p>${p}</p>`).join('')}</div>` : ''}
                </div>
            `;
        } else {
            // Regular quote section
            const reflectionHtml = section.reflection && section.reflection.includes('<')
                ? section.reflection
                : section.reflection;

            content = `
                <div class="step-content">
                    <span class="era-badge">${section.era_label}</span>
                    ${section.setup ? `<p class="setup">${section.setup}</p>` : ''}
                    ${section.quote ? `
                        <blockquote class="quote">"${section.quote}"</blockquote>
                        <p class="attribution">— ${section.speaker}, ${section.year}</p>
                    ` : ''}
                    ${section.reflection ? `<p class="reflection">${reflectionHtml}</p>` : ''}
                </div>
            `;
        }

        el.innerHTML = content;
        container.appendChild(el);
    });

    // Draw sparklines after DOM is ready
    drawSparklines();
}

// Draw sparklines for word trends
function drawSparklines() {
    document.querySelectorAll('.sparkline').forEach(svg => {
        const values = svg.dataset.values.split(',').map(Number);
        const color = svg.dataset.color;
        const width = 80;
        const height = 24;

        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

        const max = Math.max(...values);
        const min = Math.min(...values);
        const range = max - min || 1;

        const points = values.map((v, i) => {
            const x = (i / (values.length - 1)) * width;
            const y = height - ((v - min) / range) * (height - 4) - 2;
            return `${x},${y}`;
        }).join(' ');

        const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
        polyline.setAttribute('points', points);
        polyline.setAttribute('fill', 'none');
        polyline.setAttribute('stroke', color);
        polyline.setAttribute('stroke-width', '1.5');
        polyline.setAttribute('stroke-linecap', 'round');
        polyline.setAttribute('stroke-linejoin', 'round');

        svg.appendChild(polyline);
    });
}

// Initialize visualization
function initVisualization() {
    const container = domElements.timelineViz;
    const width = container.clientWidth;

    // Get responsive configuration
    const config = getResponsiveConfig();

    // Use more height on mobile
    const heightMultiplier = config.isMobile ? 0.98 : 0.92;
    const height = (container.clientHeight || 500) * heightMultiplier;
    const margin = {
        top: config.marginTop,
        right: config.marginRight,
        bottom: config.marginBottom,
        left: config.marginLeft
    };

    svg = d3.select('#timeline-viz')
        .append('svg')
        .attr('width', width)
        .attr('height', height);

    const yearGroups = d3.group(filteredParagraphs, d => d.year);
    const years = [...yearGroups.keys()].sort((a, b) => a - b);

    // Variable width calculation - now responsive
    const dotSize = config.dotSize;
    const dotGap = config.dotGap;
    const yearGap = 2;
    const maxCols = config.maxCols;

    const availableWidth = width - margin.left - margin.right;

    let yearWidths = {};
    let totalWidth = 0;

    years.forEach(year => {
        const count = yearGroups.get(year).length;
        const cols = Math.min(count, maxCols);
        const yearWidth = cols * (dotSize + dotGap) + yearGap;
        yearWidths[year] = { count, cols, width: yearWidth };
        totalWidth += yearWidth;
    });

    const scale = availableWidth / totalWidth;

    let currentX = margin.left;
    yearPositions = {};

    years.forEach(year => {
        const scaledWidth = yearWidths[year].width * scale;
        yearPositions[year] = {
            start: currentX,
            center: currentX + scaledWidth / 2,
            end: currentX + scaledWidth - yearGap * scale,
            width: scaledWidth - yearGap * scale
        };
        currentX += scaledWidth;
    });

    // Position dots - Diverging chart: promises ABOVE baseline, demands BELOW baseline
    // Calculate baseline position (middle of chart area)
    const chartHeight = height - margin.top - margin.bottom;
    const baseline = margin.top + chartHeight * 0.5; // Middle of chart

    years.forEach(year => {
        const yearParas = yearGroups.get(year);
        const yearPos = yearPositions[year];
        const effectiveWidth = yearPos.width;
        const cols = Math.max(1, Math.floor(effectiveWidth / (dotSize + dotGap)));
        const gridWidth = cols * (dotSize + dotGap);
        const offsetX = (effectiveWidth - gridWidth) / 2;

        // Separate promises and obligations
        const promises = yearParas.filter(p => p.primary_type === 'promise');
        const obligations = yearParas.filter(p => p.primary_type === 'obligation');

        // Sort promises: darker (citizen) closer to baseline, lighter (firm) further up
        promises.sort((a, b) => {
            const order = (p) => p.primary_value === 'citizen' ? 0 : 1;
            return order(a) - order(b);
        });

        // Sort obligations: darker (citizen) closer to baseline, lighter (firm) further down
        obligations.sort((a, b) => {
            const order = (p) => p.primary_value === 'citizen' ? 0 : 1;
            return order(a) - order(b);
        });

        // Position promises ABOVE baseline (going upward)
        promises.forEach((p, idx) => {
            const row = Math.floor(idx / cols);
            const col = idx % cols;

            p.xPos = yearPos.start + offsetX + col * (dotSize + dotGap) + dotSize / 2;
            p.yPos = baseline - dotSize - row * (dotSize + dotGap); // Above baseline
        });

        // Position obligations BELOW baseline (going downward)
        obligations.forEach((p, idx) => {
            const row = Math.floor(idx / cols);
            const col = idx % cols;

            p.xPos = yearPos.start + offsetX + col * (dotSize + dotGap) + dotSize / 2;
            p.yPos = baseline + dotSize + row * (dotSize + dotGap); // Below baseline
        });
    });

    // Year labels at bottom of chart
    const labelYears = [1965, 1980, 2000, 2020, 2026];
    const yearLabelOffset = config.isMobile ? 12 : 15;
    svg.selectAll('.year-label')
        .data(labelYears.filter(y => yearPositions[y]))
        .join('text')
        .attr('class', 'year-label')
        .attr('x', d => yearPositions[d].center)
        .attr('y', height - margin.bottom + yearLabelOffset)
        .attr('text-anchor', 'middle')
        .attr('fill', '#7a7a7a')
        .attr('font-size', config.fontSize.year)
        .attr('font-weight', '500')
        .style('pointer-events', 'none')
        .text(d => d)
        .raise(); // Bring to front

    // Central baseline (dividing promises above from demands below)
    svg.append('line')
        .attr('class', 'center-baseline')
        .attr('x1', margin.left)
        .attr('x2', width - margin.right)
        .attr('y1', baseline)
        .attr('y2', baseline)
        .attr('stroke', '#aaa')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,2');

    // Bottom baseline
    svg.append('line')
        .attr('x1', margin.left)
        .attr('x2', width - margin.right)
        .attr('y1', height - margin.bottom)
        .attr('y2', height - margin.bottom)
        .attr('stroke', '#d0cdc8')
        .attr('stroke-width', 1);

    // Axis labels for diverging chart
    if (!config.isMobile) {
        // "Promises" label above baseline
        svg.append('text')
            .attr('class', 'axis-label')
            .attr('x', margin.left + 5)
            .attr('y', baseline - 15)
            .attr('text-anchor', 'start')
            .attr('fill', '#C44F4F')
            .attr('font-size', '10px')
            .attr('font-weight', '600')
            .text('↑ PROMISES');

        // "Demands" label below baseline
        svg.append('text')
            .attr('class', 'axis-label')
            .attr('x', margin.left + 5)
            .attr('y', baseline + 22)
            .attr('text-anchor', 'start')
            .attr('fill', '#3D5A80')
            .attr('font-size', '10px')
            .attr('font-weight', '600')
            .text('↓ DEMANDS');
    }

    // Legend (subtle, on left side) - hide on mobile (CSS legend used instead)
    if (!config.hideSvgLegend) {
        const legendData = [
            { label: 'Promises to you', color: '#C44F4F' },
            { label: 'Promises to firms', color: '#E89898' },
            { label: "What's asked of you", color: '#2B4460' },
            { label: "What's asked of firms", color: '#6B8CAE' }
        ];

        const legendX = 30;
        const legendY = margin.top + 20;
        const legendSpacing = 18;
        const legendRectSize = 9;

        const legend = svg.append('g')
            .attr('class', 'legend')
            .attr('transform', `translate(${legendX}, ${legendY})`);

        legendData.forEach((item, i) => {
            const legendRow = legend.append('g')
                .attr('transform', `translate(0, ${i * legendSpacing})`);

            legendRow.append('rect')
                .attr('width', legendRectSize)
                .attr('height', legendRectSize)
                .attr('fill', item.color)
                .attr('opacity', 0.8);

            legendRow.append('text')
                .attr('x', legendRectSize + 5)
                .attr('y', legendRectSize - 1)
                .attr('font-size', config.fontSize.legend)
                .attr('fill', '#999')
                .attr('opacity', 0.8)
                .text(item.label);
        });
    }

    // Historical event annotations (subtle, at bottom) - hide on mobile
    if (!config.hideAnnotations) {
        const events = [
            { year: 1997, label: 'Asian Financial Crisis' },
            { year: 2020, label: 'COVID-19' }
        ];

        events.forEach(event => {
            if (yearPositions[event.year]) {
                const x = yearPositions[event.year].center;
                const lineTop = height - margin.bottom - 30;

                svg.append('line')
                    .attr('x1', x)
                    .attr('x2', x)
                    .attr('y1', lineTop)
                    .attr('y2', height - margin.bottom)
                    .attr('stroke', '#c0c0c0')
                    .attr('stroke-width', 1)
                    .attr('stroke-dasharray', '2,2')
                    .attr('opacity', 0.5);

                svg.append('text')
                    .attr('x', x)
                    .attr('y', height - margin.bottom + 32)
                    .attr('text-anchor', 'middle')
                    .attr('font-size', config.fontSize.event)
                    .attr('fill', '#888')
                    .attr('opacity', 0.7)
                    .attr('font-style', 'italic')
                    .text(event.label);
            }
        });
    }

    // Dots
    dots = svg.selectAll('.dot')
        .data(filteredParagraphs)
        .join('rect')
        .attr('class', 'dot')
        .attr('x', d => d.xPos - dotSize / 2)
        .attr('y', d => d.yPos - dotSize / 2)
        .attr('width', dotSize - 0.5)
        .attr('height', dotSize - 0.5)
        .attr('rx', 0.5)
        .attr('fill', d => {
            // Grey for none/other paragraphs
            if (!d.primary_value || d.primary_value === 'none') return '#CCCCCC';

            // Color based on type (promise/obligation) and target (citizen/firm)
            if (d.primary_type === 'promise') {
                return d.primary_value === 'citizen' ? '#C44F4F' : '#E89898'; // darker coral : lighter coral
            } else if (d.primary_type === 'obligation') {
                return d.primary_value === 'citizen' ? '#2B4460' : '#6B8CAE'; // darker blue : lighter blue
            }

            return '#b0b0b0';
        })
        .attr('opacity', 0.9)
        .attr('stroke', 'none')
        .attr('stroke-width', 0)
        .style('cursor', d => {
            // Only show pointer for promises and obligations
            return (d.primary_value && d.primary_value !== 'none') ? 'pointer' : 'default';
        })
        .on('mouseenter', function(_event, d) {
            if (!document.body.classList.contains('interactive-mode')) return;
            if (!d.primary_value || d.primary_value === 'none') return;

            // Clear pending hide timeout
            if (window.hoverPanelTimeout) {
                clearTimeout(window.hoverPanelTimeout);
                window.hoverPanelTimeout = null;
            }

            // Clear previous selection, add new selection using class
            d3.selectAll('.dot.selected').classed('selected', false);
            d3.select(this).classed('selected', true).raise();

            showHoverPanel(d);
        })
        .on('mouseleave', function(_event, d) {
            if (!document.body.classList.contains('interactive-mode')) return;
            if (!d.primary_value || d.primary_value === 'none') return;

            // Delay hiding panel and removing selection
            window.hoverPanelTimeout = setTimeout(() => {
                d3.selectAll('.dot.selected').classed('selected', false);
                hideHoverPanel();
            }, 150);
        })
        .on('click', function(_event, d) {
            if (!document.body.classList.contains('interactive-mode')) return;
            if (!d.primary_value || d.primary_value === 'none') return;

            // Clear previous, select this one
            d3.selectAll('.dot.selected').classed('selected', false);
            d3.select(this).classed('selected', true);

            showHoverPanel(d);
            pinQuote();
        });

    // Highlight box
    svg.append('rect')
        .attr('class', 'highlight-box')
        .attr('y', margin.top)
        .attr('height', height - margin.top - margin.bottom)
        .attr('fill', '#fad8ac8f')
        .attr('opacity', 0);
}

// Scroll triggers
function setupScrollTriggers() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const step = entry.target.dataset.step;
                const yearStart = parseInt(entry.target.dataset.yearStart);
                const yearEnd = parseInt(entry.target.dataset.yearEnd);

                if (step !== currentSection) {
                    currentSection = step;
                    highlightYearRange(yearStart, yearEnd);
                    updateHeader(entry.target);
                    updateProgress(yearStart, yearEnd);
                }
            }
        });
    }, {
        rootMargin: '-35% 0px -35% 0px',
        threshold: 0
    });

    document.querySelectorAll('.step').forEach(el => observer.observe(el));

    // Detect when explore section comes into view - enable interactive mode
    const exploreSection = document.querySelector('[data-step="explore"]');

    if (exploreSection) {
        const exploreObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                // Enable interactive mode when explore section is mostly visible (50%+)
                // Add delay so readers can read the explore card first
                // On mobile, interactive mode is enabled but CSS allows scrolling
                const isMobileView = window.innerWidth <= 768;
                if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
                    if (!document.body.classList.contains('interactive-mode') && !window.interactiveModeTimeout && !interactiveModeCooldown && !userExitedInteractiveMode) {

                        window.interactiveModeTimeout = setTimeout(() => {
                            document.body.classList.add('interactive-mode');

                            // Update header to show explore instructions
                            domElements.currentEra.textContent = 'Your turn';
                            const isMobileHeader = window.innerWidth <= 768;
                            domElements.currentContext.textContent = isMobileHeader
                                ? 'Tap any square to see the paragraph it represents.'
                                : 'Hover over any square to see the paragraph it represents.';

                            // Make all dots fully visible and clickable
                            if (dots) {
                                dots.transition()
                                    .duration(400)
                                    .attr('opacity', 0.9);
                            }
                            // Remove highlight box
                            if (svg) {
                                svg.select('.highlight-box')
                                    .transition()
                                    .duration(400)
                                    .attr('opacity', 0);
                            }

                            // Use requestAnimationFrame for proper repaint sync
                            requestAnimationFrame(() => {
                                const allDots = document.querySelectorAll('.dot');
                                const svgEl = document.querySelector('#timeline-viz svg');

                                // Set pointer-events on SVG element itself
                                if (svgEl) {
                                    svgEl.style.pointerEvents = 'all';
                                    // Add will-change to force GPU layer
                                    svgEl.style.willChange = 'transform';
                                }

                                // Set on each dot using both style and attribute
                                allDots.forEach(dot => {
                                    dot.style.pointerEvents = 'auto';
                                    dot.style.cursor = 'pointer';
                                    dot.setAttribute('pointer-events', 'all');
                                });

                                // Second RAF to ensure paint happens
                                requestAnimationFrame(() => {
                                    // Force a style recalc by reading layout
                                    const rect = svgEl ? svgEl.getBoundingClientRect() : null;

                                    // Add and remove a dummy class to force style recalc
                                    document.body.classList.add('force-repaint');
                                    void document.body.offsetWidth;
                                    document.body.classList.remove('force-repaint');

                                });
                            });

                            window.interactiveModeTimeout = null;
                        }, 300); // Quick trigger to prevent chart scrolling away
                    }
                } else {
                    // Not intersecting - cancel pending timeout and disable interactive mode only if not scrolled past
                    if (window.interactiveModeTimeout) {
                        clearTimeout(window.interactiveModeTimeout);
                        window.interactiveModeTimeout = null;
                    }

                    const rect = entry.boundingClientRect;
                    // On desktop, don't auto-disable interactive mode - user must explicitly exit
                    // This prevents flickering when IntersectionObserver fires during interactive mode
                    const isDesktop = window.innerWidth > 768;
                    if (rect.bottom > 0 && rect.top > window.innerHeight * 0.5) {
                        // User scrolled back up past explore section - reset the exit flag
                        userExitedInteractiveMode = false;
                        // Haven't reached it yet - only disable if not in cooldown
                        // On desktop, only disable if user explicitly exited (not from observer)
                        if (!interactiveModeCooldown && !isDesktop) {
                            document.body.classList.remove('interactive-mode');
                        }
                    } else {
                        // Scrolled past - enable interactive mode immediately (in case timeout was cancelled)
                        // On mobile, interactive mode is enabled but CSS allows scrolling
                        if (!document.body.classList.contains('interactive-mode') && !interactiveModeCooldown && !userExitedInteractiveMode) {
                            document.body.classList.add('interactive-mode');
                            domElements.currentEra.textContent = 'Your turn';
                            const isMobileHeader2 = window.innerWidth <= 768;
                            domElements.currentContext.textContent = isMobileHeader2
                                ? 'Tap any square to see the paragraph it represents.'
                                : 'Hover over any square to see the paragraph it represents.';

                            // Make all dots visible
                            if (dots) {
                                dots.attr('opacity', 0.9);
                            }
                            if (svg) {
                                svg.select('.highlight-box').attr('opacity', 0);
                            }

                            // Set pointer events
                            const allDots = document.querySelectorAll('.dot');
                            allDots.forEach(dot => {
                                dot.style.pointerEvents = 'auto';
                                dot.style.cursor = 'pointer';
                            });

                        } else {
                        }
                    }
                }
            });
        }, {
            threshold: [0, 0.1, 0.3, 0.5, 0.7, 1]
        });
        exploreObserver.observe(exploreSection);
    } else {
        console.error('❌ Explore section not found! Interactive mode will not work.');
    }
}

function highlightYearRange(start, end) {
    if (!dots) return;

    const years = Object.keys(yearPositions).map(Number).filter(y => y >= start && y <= end);

    if (years.length > 0) {
        const minX = yearPositions[Math.min(...years)].start;
        const maxX = yearPositions[Math.max(...years)].end;

        svg.select('.highlight-box')
            .attr('x', minX)
            .attr('width', maxX - minX)
            .transition()
            .duration(400)
            .attr('opacity', 0.03);
    }

    dots.transition()
        .duration(400)
        .attr('opacity', d => (d.year >= start && d.year <= end) ? 1 : 0.12);
}

function updateHeader(stepEl) {
    const section = storyData.sections.find(s => s.id === stepEl.dataset.step);
    if (section) {
        // Use header_text if available, otherwise fall back to era_label
        domElements.currentEra.textContent = section.header_text || section.era_label;
        domElements.currentContext.textContent = section.title;
    }
}

function updateProgress(start, end) {
    const midpoint = (start + end) / 2;
    const progress = (midpoint - 1965) / (2026 - 1965);
    domElements.progressFill.style.width = `${Math.min(100, progress * 100)}%`;
}

// Modal
function setupModal() {
    const modal = domElements.quoteModal;
    modal.querySelector('.modal-close').addEventListener('click', () => modal.classList.add('hidden'));
    modal.addEventListener('click', e => { if (e.target === modal) modal.classList.add('hidden'); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') modal.classList.add('hidden'); });
}


function showModal(d) {
    const modal = domElements.quoteModal;
    if (!modal) {
        console.error('Modal element not found!');
        return;
    }
    modal.querySelector('.modal-year').textContent = d.year;
    modal.querySelector('.modal-fm').textContent = d.fm_name || '';
    modal.querySelector('.modal-quote').textContent = d.text;

    // Only show primary tag
    const promTag = modal.querySelector('.promise-tag');
    const oblTag = modal.querySelector('.obligation-tag');

    if (d.primary_type === 'promise') {
        promTag.textContent = d.primary_value === 'citizen' ? 'Promise (citizen)' : 'Promise (firm)';
        promTag.style.background = d.primary_value === 'citizen' ? '#C44F4F' : '#E89898';
        oblTag.textContent = '';
    } else if (d.primary_type === 'obligation') {
        oblTag.textContent = d.primary_value === 'citizen' ? 'Obligation (citizen)' : 'Obligation (firm)';
        oblTag.style.background = d.primary_value === 'citizen' ? '#2B4460' : '#6B8CAE';
        promTag.textContent = '';
    }

    modal.classList.remove('hidden');
}

// Hover panel functions for interactive mode
function showHoverPanel(d) {

    const panel = domElements.hoverPanel;
    if (!panel) {
        console.error('Hover panel not found!');
        return;
    }

    panel.querySelector('.hover-panel-year').textContent = d.year;
    panel.querySelector('.hover-panel-fm').textContent = d.fm_name || '';
    panel.querySelector('.hover-panel-quote').textContent = `"${d.text}"`;

    const tag = panel.querySelector('.hover-panel-tag');
    if (d.primary_type === 'promise') {
        tag.textContent = d.primary_value === 'citizen' ? 'Promise to citizens' : 'Promise to firms';
        tag.style.background = d.primary_value === 'citizen' ? '#C44F4F' : '#E89898';
        tag.style.color = '#fff';
    } else if (d.primary_type === 'obligation') {
        tag.textContent = d.primary_value === 'citizen' ? 'Asked of citizens' : 'Asked of firms';
        tag.style.background = d.primary_value === 'citizen' ? '#2B4460' : '#6B8CAE';
        tag.style.color = '#fff';
    } else {
        tag.textContent = '';
    }

    panel.classList.remove('hidden');
}

function hideHoverPanel() {
    const panel = domElements.hoverPanel;
    // Don't hide if pinned
    if (panel && !panel.classList.contains('pinned')) {
        panel.classList.add('hidden');
    }
}

function pinQuote() {
    const panel = domElements.hoverPanel;
    if (panel) {
        panel.classList.add('pinned');
    }
}

function unpinQuote() {
    const panel = domElements.hoverPanel;
    if (panel) {
        panel.classList.remove('pinned');
        panel.classList.add('hidden');
    }
}

// Resize (also handles orientation change)
window.addEventListener('resize', debounce(() => {
    domElements.timelineViz.innerHTML = '';
    initVisualization();
}, 250));

function debounce(fn, wait) {
    let t;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), wait);
    };
}

// Close pinned panel when clicking outside
document.addEventListener('click', function(e) {
    const panel = domElements.hoverPanel;
    // If panel is pinned and click is outside the panel and not on a dot
    if (panel && panel.classList.contains('pinned')) {
        if (!panel.contains(e.target) && !e.target.classList.contains('dot')) {
            unpinQuote();
        }
    }
});


// Exit interactive mode and allow free scrolling
let interactiveModeCooldown = false;
let userExitedInteractiveMode = false; // Track if user manually exited

function exitInteractiveMode() {

    // Set cooldown to prevent immediate re-trigger
    interactiveModeCooldown = true;
    userExitedInteractiveMode = true; // User manually exited, don't auto-enable again

    // Remove overflow:hidden so we can scroll
    document.body.style.overflow = '';
    document.body.classList.remove('interactive-mode');

    // Hide hover panel
    const panel = domElements.hoverPanel;
    if (panel) panel.classList.add('hidden');

    // Reset dots opacity
    const allDots = document.querySelectorAll('.dot');
    allDots.forEach(dot => {
        dot.style.pointerEvents = 'none';
    });


    // Clear cooldown after 3 seconds
    setTimeout(() => {
        interactiveModeCooldown = false;
    }, 3000);
}

// Exit interactive mode and scroll to top (for mobile button)
function exitInteractiveModeAndScrollTop() {
    exitInteractiveMode();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Allow scrolling up to exit interactive mode (desktop)
// Track cumulative scroll to require sustained scrolling
let cumulativeScrollUp = 0;
let scrollResetTimeout = null;

document.addEventListener('wheel', function(e) {
    if (!document.body.classList.contains('interactive-mode')) return;

    // Reset cumulative scroll after 500ms of no scrolling
    if (scrollResetTimeout) {
        clearTimeout(scrollResetTimeout);
    }
    scrollResetTimeout = setTimeout(() => {
        cumulativeScrollUp = 0;
    }, 500);

    // Only track upward scrolling (negative deltaY)
    if (e.deltaY < 0) {
        cumulativeScrollUp += Math.abs(e.deltaY);
    } else {
        // Scrolling down resets the counter
        cumulativeScrollUp = 0;
    }

    // Require significant sustained upward scroll to exit (300+ pixels worth)
    if (cumulativeScrollUp > 300) {
        cumulativeScrollUp = 0;
        exitInteractiveMode();
    }
}, { passive: true });

// Escape key to exit interactive mode (desktop)
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && document.body.classList.contains('interactive-mode')) {
        exitInteractiveMode();
    }
});

// Touch swipe to exit interactive mode (mobile)
let touchStartY = 0;
let touchStartTime = 0;

document.addEventListener('touchstart', function(e) {
    if (!document.body.classList.contains('interactive-mode')) return;
    touchStartY = e.touches[0].clientY;
    touchStartTime = Date.now();
}, { passive: true });

document.addEventListener('touchend', function(e) {
    if (!document.body.classList.contains('interactive-mode')) return;

    const touchEndY = e.changedTouches[0].clientY;
    const touchEndTime = Date.now();
    const deltaY = touchEndY - touchStartY;
    const deltaTime = touchEndTime - touchStartTime;

    // Detect swipe down (finger moves down = scroll up intent) - quick swipe of at least 50px
    if (deltaY > 50 && deltaTime < 300) {
        exitInteractiveMode();
    }
}, { passive: true });
