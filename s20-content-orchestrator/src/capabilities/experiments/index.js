/**
 * ExperimentEngine - Orchestrates topic exploration and engagement optimization
 * Combines A/B testing with topic discovery to improve content strategy
 */

import { config } from '../../../config/defaults.js';
import ABTestRunner from './ab-test.js';
import TopicsExplorer from './topics.js';

class ExperimentEngine {
  constructor(stateManager, contentFactory, twitterService, options = {}) {
    this.stateManager = stateManager;
    this.contentFactory = contentFactory;
    this.twitterService = twitterService;
    this.config = { ...config, ...options };
    
    // Initialize sub-components
    this.abTestRunner = new ABTestRunner(stateManager);
    this.topicsExplorer = new TopicsExplorer(stateManager, twitterService, options);
    
    // Learning accumulation
    this.learnings = [];
    this.initialized = false;
  }

  /**
   * Initialize the experiment engine
   */
  async init() {
    if (this.initialized) return this;
    
    await this.abTestRunner.init();
    await this.topicsExplorer.init();
    await this._loadLearnings();
    
    this.initialized = true;
    return this;
  }

  /**
   * Load accumulated learnings from state
   */
  async _loadLearnings() {
    const stored = this.stateManager.get('experiment_learnings');
    if (stored && Array.isArray(stored)) {
      this.learnings = stored;
    }
  }

  // ===========================================
  // Topic Exploration
  // ===========================================

  /**
   * Discover new trending topics in the niche
   * @param {Object} options - Discovery options
   * @returns {Array} Discovered topics
   */
  async exploreTopics(options = {}) {
    this._ensureInitialized();

    const results = {
      topics: [],
      gaps: [],
      patterns: [],
      timestamp: new Date().toISOString()
    };

    // Discover trending topics
    results.topics = await this.topicsExplorer.discoverTrendingTopics();

    // Analyze engagement patterns
    results.patterns = await this.topicsExplorer.analyzeEngagementPatterns(
      options.daysBack || 30
    );

    // Identify content gaps
    results.gaps = await this.topicsExplorer.identifyNicheGaps();

    // Log exploration activity
    this.stateManager.logAction({
      module: 'experiments',
      action: 'exploreTopics',
      result: `Found ${results.topics.length} topics, ${results.gaps.length} gaps`
    });

    return results;
  }

  /**
   * Get topics ready for content generation
   * @param {number} limit - Maximum topics to return
   * @returns {Array} Prioritized topics
   */
  getTopicsForContent(limit = 10) {
    return this.topicsExplorer.getTopicsForContent(limit);
  }

  /**
   * Mark a topic as covered in content
   * @param {string} topic - Topic keyword
   */
  markTopicCovered(topic) {
    this.topicsExplorer.markTopicCovered(topic);
  }

  // ===========================================
  // A/B Testing
  // ===========================================

  /**
   * Start a new A/B test experiment
   * @param {string} name - Unique experiment name
   * @param {string} hypothesis - What we're testing
   * @param {Array} variants - Array of {id, config} objects
   * @param {Object} options - Test options
   * @returns {Object} Created test
   */
  startExperiment(name, hypothesis, variants, options = {}) {
    this._ensureInitialized();

    const test = this.abTestRunner.createTest(name, hypothesis, variants, options);

    this.stateManager.logAction({
      module: 'experiments',
      action: 'startExperiment',
      params: { name, hypothesis },
      result: `Test created with ${variants.length} variants`
    });

    return test;
  }

  /**
   * Get a variant assignment for an experiment
   * @param {string|number} testId - Test ID or name
   * @returns {Object} Assigned variant
   */
  getExperimentVariant(testId) {
    return this.abTestRunner.assignVariant(testId);
  }

  /**
   * Record results for an experiment variant
   * @param {string|number} testId - Test ID
   * @param {string} variantId - Variant ID
   * @param {Object} metrics - Performance metrics
   */
  recordExperimentResult(testId, variantId, metrics) {
    return this.abTestRunner.recordResult(testId, variantId, metrics);
  }

  /**
   * Get all active experiments
   * @returns {Array} Active tests
   */
  getActiveExperiments() {
    return this.abTestRunner.getActiveTests();
  }

  /**
   * Analyze results for a specific test
   * @param {string|number} testId - Test ID or name
   * @returns {Object} Analysis results
   */
  analyzeTest(testId) {
    return this.abTestRunner.analyzeTest(testId);
  }

  /**
   * End an experiment
   * @param {string|number} testId - Test ID
   * @returns {Object} Final analysis
   */
  endExperiment(testId) {
    return this.abTestRunner.endTest(testId);
  }

  // ===========================================
  // Analysis & Learnings
  // ===========================================

  /**
   * Analyze all experiments and extract learnings
   * @returns {Object} Comprehensive analysis
   */
  async analyzeExperiments() {
    this._ensureInitialized();

    const analysis = {
      activeTests: [],
      completedTests: [],
      learnings: [],
      recommendations: [],
      timestamp: new Date().toISOString()
    };

    // Analyze active tests
    const activeTests = this.abTestRunner.getActiveTests();
    for (const test of activeTests) {
      const testAnalysis = this.abTestRunner.analyzeTest(test.id);
      analysis.activeTests.push(testAnalysis);
    }

    // Get completed tests from database
    const completedTests = this.stateManager.query(
      `SELECT * FROM experiments WHERE end_date IS NOT NULL ORDER BY end_date DESC`
    );

    for (const test of completedTests) {
      const results = typeof test.results === 'string' 
        ? JSON.parse(test.results) 
        : test.results;
      analysis.completedTests.push({
        name: test.name,
        hypothesis: test.hypothesis,
        results
      });
    }

    // Extract new learnings from analyses
    const newLearnings = this._extractLearnings(analysis);
    analysis.learnings = newLearnings;

    // Generate recommendations
    analysis.recommendations = this._generateRecommendations(analysis);

    // Store learnings
    for (const learning of newLearnings) {
      this.stateManager.addLearning(learning);
      this.learnings.push(learning);
    }
    this.stateManager.set('experiment_learnings', this.learnings);

    return analysis;
  }

  /**
   * Retrieve accumulated insights
   * @param {string} category - Optional category filter
   * @returns {Array} Learnings
   */
  getLearnings(category = null) {
    if (category) {
      return this.stateManager.getLearningsByCategory(category);
    }
    return this.learnings;
  }

  /**
   * Use insights to improve future content
   * @param {Object} contentConfig - Content configuration to enhance
   * @returns {Object} Enhanced configuration
   */
  applyLearnings(contentConfig = {}) {
    this._ensureInitialized();

    const enhanced = { ...contentConfig };

    // Apply best practices from learnings
    for (const learning of this.learnings) {
      if (learning.confidence < 0.6) continue; // Skip low-confidence learnings

      switch (learning.category) {
        case 'timing':
          enhanced.postingTime = enhanced.postingTime || learning.insight;
          break;

        case 'format':
          enhanced.preferredFormat = enhanced.preferredFormat || learning.insight;
          break;

        case 'hashtag':
          enhanced.hashtagStrategy = enhanced.hashtagStrategy || learning.insight;
          break;

        case 'tone':
          enhanced.tone = enhanced.tone || learning.insight;
          break;

        case 'topic':
          if (!enhanced.topicPriorities) enhanced.topicPriorities = [];
          enhanced.topicPriorities.push(learning.insight);
          break;

        default:
          if (!enhanced.generalTips) enhanced.generalTips = [];
          enhanced.generalTips.push(learning.insight);
      }
    }

    // Apply engagement pattern learnings
    const patterns = this.topicsExplorer.engagementPatterns;
    for (const pattern of patterns) {
      if (pattern.type === 'timing' && pattern.performance === 'excellent') {
        enhanced.optimalTimeSlot = pattern.slot;
      }
      if (pattern.type === 'hashtag_count' && pattern.performance === 'optimal') {
        enhanced.optimalHashtagCount = pattern.category;
      }
    }

    // Add topic suggestions
    enhanced.suggestedTopics = this.getTopicsForContent(5);

    return enhanced;
  }

  // ===========================================
  // Experiment Templates
  // ===========================================

  /**
   * Create a tone variation experiment
   * @param {string} baseContent - Base content to test
   * @returns {Object} Created test
   */
  createToneExperiment(baseContent) {
    return this.startExperiment(
      `tone_test_${Date.now()}`,
      'Which tone generates more engagement?',
      [
        { id: 'professional', config: { tone: 'professional', content: baseContent } },
        { id: 'casual', config: { tone: 'casual', content: baseContent } },
        { id: 'enthusiastic', config: { tone: 'enthusiastic', content: baseContent } }
      ]
    );
  }

  /**
   * Create a posting time experiment
   * @param {string} content - Content to post
   * @returns {Object} Created test
   */
  createTimingExperiment(content) {
    return this.startExperiment(
      `timing_test_${Date.now()}`,
      'Which posting time gets more engagement?',
      [
        { id: 'morning', config: { content, postAt: '09:00' } },
        { id: 'afternoon', config: { content, postAt: '14:00' } },
        { id: 'evening', config: { content, postAt: '19:00' } }
      ]
    );
  }

  /**
   * Create a hashtag experiment
   * @param {string} content - Base content
   * @param {Array} hashtagSets - Different hashtag combinations
   * @returns {Object} Created test
   */
  createHashtagExperiment(content, hashtagSets) {
    return this.startExperiment(
      `hashtag_test_${Date.now()}`,
      'Which hashtag strategy works better?',
      hashtagSets.map((hashtags, i) => ({
        id: `variant_${i + 1}`,
        config: { content, hashtags }
      }))
    );
  }

  /**
   * Create a format experiment (thread vs single tweet)
   * @param {string} topic - Topic to cover
   * @returns {Object} Created test
   */
  createFormatExperiment(topic) {
    return this.startExperiment(
      `format_test_${Date.now()}`,
      'Which content format generates more engagement?',
      [
        { id: 'single_tweet', config: { format: 'tweet', topic } },
        { id: 'thread', config: { format: 'thread', topic, threadLength: 5 } }
      ]
    );
  }

  // ===========================================
  // Helper Methods
  // ===========================================

  /**
   * Ensure engine is initialized
   */
  _ensureInitialized() {
    if (!this.initialized) {
      throw new Error('ExperimentEngine not initialized. Call init() first.');
    }
  }

  /**
   * Extract learnings from experiment analyses
   */
  _extractLearnings(analysis) {
    const learnings = [];

    // Extract from active tests
    for (const test of analysis.activeTests) {
      if (test.confidence >= 0.8 && test.winner) {
        const winner = test.variants.find(v => v.id === test.winner);
        if (winner) {
          learnings.push({
            category: this._categorizeTest(test.testName),
            insight: this._formatInsight(test.testName, winner.config),
            evidence: { testName: test.testName, winner: test.winner, confidence: test.confidence },
            confidence: test.confidence,
            applicableTo: ['content_generation']
          });
        }
      }
    }

    // Extract from engagement patterns
    for (const pattern of this.topicsExplorer.engagementPatterns) {
      if (pattern.performance === 'excellent' || pattern.performance === 'good') {
        learnings.push({
          category: pattern.type || 'general',
          insight: this._formatPatternInsight(pattern),
          evidence: pattern,
          confidence: pattern.performance === 'excellent' ? 0.85 : 0.7,
          applicableTo: ['content_generation', 'posting_schedule']
        });
      }
    }

    return learnings;
  }

  /**
   * Generate recommendations based on analysis
   */
  _generateRecommendations(analysis) {
    const recommendations = [];

    for (const test of analysis.activeTests) {
      if (test.recommendation) {
        recommendations.push({
          source: test.testName,
          recommendation: test.recommendation,
          confidence: test.confidence,
          action: this._suggestAction(test)
        });
      }
    }

    // Add topic-based recommendations
    const gaps = this.topicsExplorer.getTopicsForContent(5);
    for (const gap of gaps) {
      if (gap.priority >= 70) {
        recommendations.push({
          source: 'topic_analysis',
          recommendation: `Create content about: ${gap.topic}`,
          confidence: 0.7,
          action: 'generate_content'
        });
      }
    }

    return recommendations;
  }

  /**
   * Categorize test by name
   */
  _categorizeTest(testName) {
    if (testName.includes('tone')) return 'tone';
    if (testName.includes('timing')) return 'timing';
    if (testName.includes('hashtag')) return 'hashtag';
    if (testName.includes('format')) return 'format';
    return 'general';
  }

  /**
   * Format insight from test results
   */
  _formatInsight(testName, config) {
    if (testName.includes('tone')) {
      return `${config.tone} tone performs best`;
    }
    if (testName.includes('timing')) {
      return `Post at ${config.postAt} for best results`;
    }
    if (testName.includes('hashtag')) {
      return `Use hashtags: ${Array.isArray(config.hashtags) ? config.hashtags.join(', ') : config.hashtags}`;
    }
    if (testName.includes('format')) {
      return `${config.format} format works best`;
    }
    return JSON.stringify(config);
  }

  /**
   * Format pattern insight
   */
  _formatPatternInsight(pattern) {
    if (pattern.type === 'timing') {
      return `${pattern.slot} posting yields ${pattern.performance} engagement`;
    }
    if (pattern.type === 'hashtag_count') {
      return `${pattern.category} hashtags is ${pattern.performance}`;
    }
    if (pattern.type && pattern.avgEngagement) {
      return `${pattern.type} content averages ${pattern.avgEngagement.toFixed(1)} engagements`;
    }
    return JSON.stringify(pattern);
  }

  /**
   * Suggest action based on test results
   */
  _suggestAction(test) {
    if (test.confidence >= 0.95) {
      return 'adopt_immediately';
    }
    if (test.confidence >= 0.80) {
      return 'consider_adoption';
    }
    return 'continue_testing';
  }
}

export default ExperimentEngine;
export { ABTestRunner, TopicsExplorer };
