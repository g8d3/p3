/**
 * A/B Test Runner - Handles experiment creation, variant assignment, and analysis
 * Supports testing different content strategies: tones, posting times, hashtags, formats
 */

import { config } from '../../../config/defaults.js';

class ABTestRunner {
  constructor(stateManager) {
    this.stateManager = stateManager;
    this.activeTests = new Map();
  }

  /**
   * Initialize the test runner and load active tests
   */
  async init() {
    await this._loadActiveTests();
    return this;
  }

  /**
   * Load active tests from database into memory
   */
  async _loadActiveTests() {
    const tests = this.stateManager.getActiveExperiments();
    for (const test of tests) {
      const parsedTest = {
        ...test,
        variants: JSON.parse(test.variants || '[]'),
        results: JSON.parse(test.results || '{}')
      };
      this.activeTests.set(test.id, parsedTest);
    }
  }

  /**
   * Create a new A/B test
   * @param {string} name - Unique test name
   * @param {string} hypothesis - What we're testing and why
   * @param {Array} variants - Array of {id, config} objects
   * @param {Object} options - Optional: startDate, endDate, sampleSize
   * @returns {Object} Created test
   */
  createTest(name, hypothesis, variants, options = {}) {
    if (!name || !variants || variants.length < 2) {
      throw new Error('Test requires name and at least 2 variants');
    }

    // Validate variants have required structure
    for (const variant of variants) {
      if (!variant.id || !variant.config) {
        throw new Error('Each variant must have id and config');
      }
    }

    const test = {
      name,
      hypothesis,
      variants: variants.map(v => ({
        id: v.id,
        config: v.config,
        assignments: 0,
        results: []
      })),
      startDate: options.startDate || new Date().toISOString(),
      endDate: options.endDate || null,
      sampleSize: options.sampleSize || 100,
      status: 'running'
    };

    // Persist to database
    const result = this.stateManager.createExperiment({
      name: test.name,
      hypothesis: test.hypothesis,
      startDate: test.startDate,
      endDate: test.endDate,
      variants: test.variants
    });

    // Get the inserted ID
    const dbTest = this.stateManager.queryOne(
      'SELECT id FROM experiments WHERE name = ?',
      [name]
    );
    
    test.id = dbTest.id;
    test.results = {};
    this.activeTests.set(test.id, test);

    return test;
  }

  /**
   * Get a test by ID or name
   * @param {number|string} testId - Test ID or name
   * @returns {Object|null} Test object
   */
  getTest(testId) {
    // If it's a string, look up by name
    if (typeof testId === 'string') {
      const test = this.stateManager.queryOne(
        'SELECT * FROM experiments WHERE name = ?',
        [testId]
      );
      if (!test) return null;
      testId = test.id;
    }
    return this.activeTests.get(testId) || null;
  }

  /**
   * Get all active tests
   * @returns {Array} List of active tests
   */
  getActiveTests() {
    return Array.from(this.activeTests.values());
  }

  /**
   * Assign a user/session to a variant randomly
   * Uses weighted random if variant weights are specified
   * @param {number} testId - Test ID
   * @returns {Object} Assigned variant {id, config}
   */
  assignVariant(testId) {
    const test = this.getTest(testId);
    if (!test) {
      throw new Error(`Test not found: ${testId}`);
    }

    if (test.status !== 'running') {
      throw new Error(`Test is not running: ${test.name}`);
    }

    // Calculate weights (default to equal distribution)
    const weights = test.variants.map(v => v.weight || 1);
    const totalWeight = weights.reduce((sum, w) => sum + w, 0);

    // Weighted random selection
    let random = Math.random() * totalWeight;
    let selectedVariant = test.variants[0];

    for (let i = 0; i < test.variants.length; i++) {
      random -= weights[i];
      if (random <= 0) {
        selectedVariant = test.variants[i];
        break;
      }
    }

    // Update assignment count
    selectedVariant.assignments = (selectedVariant.assignments || 0) + 1;
    this._persistTest(test);

    return {
      id: selectedVariant.id,
      config: selectedVariant.config,
      testId: test.id,
      testName: test.name
    };
  }

  /**
   * Record a result for a variant
   * @param {number} testId - Test ID
   * @param {string} variantId - Variant ID
   * @param {Object} metrics - Performance metrics
   */
  recordResult(testId, variantId, metrics) {
    const test = this.getTest(testId);
    if (!test) {
      throw new Error(`Test not found: ${testId}`);
    }

    const variant = test.variants.find(v => v.id === variantId);
    if (!variant) {
      throw new Error(`Variant not found: ${variantId}`);
    }

    // Initialize results structure if needed
    if (!variant.results) {
      variant.results = [];
    }

    // Store the result with timestamp
    const result = {
      timestamp: new Date().toISOString(),
      ...metrics
    };
    variant.results.push(result);

    // Persist to database
    this._persistTest(test);

    return result;
  }

  /**
   * Analyze test results with statistical comparison
   * @param {number} testId - Test ID
   * @returns {Object} Analysis results
   */
  analyzeTest(testId) {
    const test = this.getTest(testId);
    if (!test) {
      throw new Error(`Test not found: ${testId}`);
    }

    const analysis = {
      testName: test.name,
      hypothesis: test.hypothesis,
      status: test.status,
      totalAssignments: 0,
      variants: [],
      winner: null,
      confidence: 0,
      recommendation: null
    };

    let bestVariant = null;
    let bestScore = -Infinity;

    for (const variant of test.variants) {
      const results = variant.results || [];
      const assignments = variant.assignments || 0;
      analysis.totalAssignments += assignments;

      // Calculate aggregate metrics
      const metrics = this._aggregateMetrics(results);
      
      // Calculate engagement rate
      const engagementRate = assignments > 0 
        ? (metrics.totalEngagements / assignments) * 100 
        : 0;

      // Calculate conversion rate if applicable
      const conversionRate = metrics.impressions > 0
        ? (metrics.conversions / metrics.impressions) * 100
        : 0;

      const variantAnalysis = {
        id: variant.id,
        config: variant.config,
        assignments,
        totalResults: results.length,
        metrics,
        engagementRate: engagementRate.toFixed(2),
        conversionRate: conversionRate.toFixed(2),
        avgEngagement: metrics.avgEngagement.toFixed(2)
      };

      analysis.variants.push(variantAnalysis);

      // Determine winner based on engagement score
      const score = this._calculateScore(metrics, assignments);
      if (score > bestScore) {
        bestScore = score;
        bestVariant = variantAnalysis;
      }
    }

    // Statistical significance check (simplified)
    if (bestVariant && analysis.totalAssignments >= 30) {
      analysis.winner = bestVariant.id;
      analysis.confidence = this._calculateConfidence(test.variants, bestVariant);
      
      if (analysis.confidence >= 0.95) {
        analysis.recommendation = `Strong evidence: Adopt variant "${bestVariant.id}" configuration`;
      } else if (analysis.confidence >= 0.80) {
        analysis.recommendation = `Moderate evidence: Consider adopting variant "${bestVariant.id}"`;
      } else {
        analysis.recommendation = 'Insufficient evidence: Continue testing';
      }
    } else {
      analysis.recommendation = 'Need more data for statistical significance (min 30 assignments)';
    }

    return analysis;
  }

  /**
   * End a test and finalize results
   * @param {number} testId - Test ID
   * @returns {Object} Final analysis
   */
  endTest(testId) {
    const test = this.getTest(testId);
    if (!test) {
      throw new Error(`Test not found: ${testId}`);
    }

    test.status = 'completed';
    test.endDate = new Date().toISOString();

    const analysis = this.analyzeTest(testId);
    test.results = analysis;

    this._persistTest(test);
    this.activeTests.delete(testId);

    return analysis;
  }

  /**
   * Aggregate metrics from results array
   */
  _aggregateMetrics(results) {
    if (!results || results.length === 0) {
      return {
        likes: 0,
        retweets: 0,
        replies: 0,
        impressions: 0,
        conversions: 0,
        totalEngagements: 0,
        avgEngagement: 0
      };
    }

    const totals = results.reduce((acc, r) => ({
      likes: acc.likes + (r.likes || 0),
      retweets: acc.retweets + (r.retweets || 0),
      replies: acc.replies + (r.replies || 0),
      impressions: acc.impressions + (r.impressions || 0),
      conversions: acc.conversions + (r.conversions || 0)
    }), { likes: 0, retweets: 0, replies: 0, impressions: 0, conversions: 0 });

    totals.totalEngagements = totals.likes + totals.retweets + totals.replies;
    totals.avgEngagement = results.length > 0 
      ? totals.totalEngagements / results.length 
      : 0;

    return totals;
  }

  /**
   * Calculate a composite score for variant comparison
   */
  _calculateScore(metrics, assignments) {
    // Weighted score: prioritize engagement rate and volume
    const engagementScore = metrics.avgEngagement * 10;
    const volumeScore = Math.log10(assignments + 1) * 5;
    const conversionBonus = metrics.conversions * 2;
    
    return engagementScore + volumeScore + conversionBonus;
  }

  /**
   * Calculate confidence level (simplified statistical test)
   */
  _calculateConfidence(variants, bestVariant) {
    // Simplified confidence calculation based on sample size and effect size
    const minSampleSize = 30;
    const bestSample = bestVariant.assignments;
    
    if (bestSample < minSampleSize) {
      return 0;
    }

    // Calculate effect size (difference from average)
    const avgEngagement = variants.reduce((sum, v) => {
      const results = v.results || [];
      const metrics = this._aggregateMetrics(results);
      return sum + metrics.avgEngagement;
    }, 0) / variants.length;

    const effectSize = Math.abs(bestVariant.avgEngagement - avgEngagement) / (avgEngagement || 1);
    
    // Confidence increases with sample size and effect size
    const sampleConfidence = Math.min(bestSample / 100, 0.5);
    const effectConfidence = Math.min(effectSize * 2, 0.5);
    
    return Math.min(sampleConfidence + effectConfidence, 0.99);
  }

  /**
   * Persist test state to database
   */
  _persistTest(test) {
    this.stateManager.query(
      `UPDATE experiments 
       SET variants = ?, results = ?, end_date = ?
       WHERE id = ?`,
      [
        JSON.stringify(test.variants),
        JSON.stringify(test.results || {}),
        test.endDate,
        test.id
      ]
    );
  }
}

export default ABTestRunner;
