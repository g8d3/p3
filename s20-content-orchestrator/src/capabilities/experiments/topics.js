/**
 * Topics Explorer - Discovers trending topics and engagement patterns
 * Focuses on niche areas defined in config.identity.focus
 */

import { config } from '../../../config/defaults.js';

class TopicsExplorer {
  constructor(stateManager, twitterService, options = {}) {
    this.stateManager = stateManager;
    this.twitterService = twitterService;
    this.focusAreas = options.focusAreas || config.identity.focus || [];
    this.discoveredTopics = [];
    this.engagementPatterns = [];
  }

  /**
   * Initialize the explorer
   */
  async init() {
    await this._loadCachedTopics();
    return this;
  }

  /**
   * Load previously discovered topics from state
   */
  async _loadCachedTopics() {
    const cached = this.stateManager.get('discovered_topics');
    if (cached && Array.isArray(cached)) {
      this.discoveredTopics = cached;
    }
  }

  /**
   * Get configured focus areas
   * @returns {Array} Focus areas from config
   */
  getFocusAreas() {
    return this.focusAreas;
  }

  /**
   * Discover trending topics in the niche
   * Scans X.com for trends related to focus areas
   * @returns {Array} Discovered trending topics
   */
  async discoverTrendingTopics() {
    const topics = [];

    for (const focusArea of this.focusAreas) {
      try {
        // Search for trending content related to focus area
        const searchResults = await this._searchTrends(focusArea);
        
        for (const result of searchResults) {
          const topic = {
            id: this._generateTopicId(result),
            keyword: result.keyword || focusArea,
            relatedHashtags: result.hashtags || [],
            volume: result.volume || 'unknown',
            sentiment: result.sentiment || 'neutral',
            focusArea,
            discoveredAt: new Date().toISOString(),
            sources: result.sources || []
          };

          topics.push(topic);
        }
      } catch (error) {
        console.error(`Error discovering topics for ${focusArea}:`, error.message);
      }
    }

    // Deduplicate and merge with existing topics
    this._mergeTopics(topics);

    // Persist to state
    this._persistTopics();

    return this.discoveredTopics;
  }

  /**
   * Search for trends using Twitter service
   * @param {string} focusArea - Area to search
   * @returns {Array} Search results
   */
  async _searchTrends(focusArea) {
    const results = [];

    // If twitter service is available, use it to search
    if (this.twitterService && typeof this.twitterService.searchTweets === 'function') {
      try {
        const tweets = await this.twitterService.searchTweets(focusArea, { count: 50 });
        
        // Extract hashtags and keywords from tweets
        const hashtagCounts = new Map();
        const keywordCounts = new Map();

        for (const tweet of tweets) {
          // Extract hashtags
          const hashtags = this._extractHashtags(tweet.text);
          for (const tag of hashtags) {
            hashtagCounts.set(tag, (hashtagCounts.get(tag) || 0) + 1);
          }

          // Extract keywords
          const keywords = this._extractKeywords(tweet.text, focusArea);
          for (const kw of keywords) {
            keywordCounts.set(kw, (keywordCounts.get(kw) || 0) + 1);
          }
        }

        // Convert to results format
        for (const [hashtag, count] of hashtagCounts) {
          if (count >= 3) { // Only include hashtags mentioned 3+ times
            results.push({
              keyword: hashtag,
              hashtags: [hashtag],
              volume: count,
              sentiment: 'neutral',
              sources: ['twitter_search']
            });
          }
        }

        for (const [keyword, count] of keywordCounts) {
          if (count >= 2 && !results.find(r => r.keyword === keyword)) {
            results.push({
              keyword,
              hashtags: [],
              volume: count,
              sentiment: 'neutral',
              sources: ['twitter_search']
            });
          }
        }
      } catch (error) {
        console.error('Twitter search failed:', error.message);
      }
    }

    // Generate synthetic topics based on focus area patterns
    const syntheticTopics = this._generateSyntheticTopics(focusArea);
    results.push(...syntheticTopics);

    return results;
  }

  /**
   * Generate synthetic topics based on known patterns
   * Used when Twitter API is unavailable
   */
  _generateSyntheticTopics(focusArea) {
    const topicPatterns = {
      'AI agents': [
        { keyword: 'autonomous agents', hashtags: ['#AIAgents', '#AutonomousAI'], volume: 'high' },
        { keyword: 'agent frameworks', hashtags: ['#LangChain', '#AutoGPT'], volume: 'medium' },
        { keyword: 'multi-agent systems', hashtags: ['#MultiAgent', '#AgentSwarm'], volume: 'medium' },
        { keyword: 'agent memory', hashtags: ['#AgentMemory', '#AIContext'], volume: 'low' }
      ],
      'automation': [
        { keyword: 'workflow automation', hashtags: ['#Automation', '#NoCode'], volume: 'high' },
        { keyword: 'AI automation', hashtags: ['#AIAutomation', '#AutoML'], volume: 'medium' },
        { keyword: 'RPA alternatives', hashtags: ['#RPA', '#AutomationTools'], volume: 'medium' }
      ],
      'building in public': [
        { keyword: 'startup journey', hashtags: ['#BuildInPublic', '#StartupLife'], volume: 'high' },
        { keyword: 'MVP launch', hashtags: ['#MVP', '#ProductLaunch'], volume: 'medium' },
        { keyword: 'indie hackers', hashtags: ['#IndieHackers', '#Solopreneur'], volume: 'high' }
      ],
      'coding': [
        { keyword: 'AI coding assistants', hashtags: ['#AICoding', '#GitHubCopilot'], volume: 'high' },
        { keyword: 'developer productivity', hashtags: ['#DevTools', '#CodingTips'], volume: 'medium' },
        { keyword: 'code review automation', hashtags: ['#CodeReview', '#DevOps'], volume: 'low' }
      ]
    };

    return (topicPatterns[focusArea] || []).map(t => ({
      ...t,
      sentiment: 'positive',
      sources: ['pattern_analysis']
    }));
  }

  /**
   * Analyze what content types work best
   * @param {number} daysBack - Number of days to analyze
   * @returns {Array} Engagement patterns
   */
  async analyzeEngagementPatterns(daysBack = 30) {
    const patterns = [];
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - daysBack);

    // Get posted content with engagement metrics
    const contentItems = this.stateManager.query(
      `SELECT * FROM content_items 
       WHERE status = 'posted' 
       AND posted_at >= ?
       ORDER BY posted_at DESC`,
      [startDate.toISOString()]
    );

    if (!contentItems || contentItems.length === 0) {
      return this._getDefaultPatterns();
    }

    // Analyze by content type
    const typeGroups = this._groupBy(contentItems, 'type');
    for (const [type, items] of Object.entries(typeGroups)) {
      const avgEngagement = this._calculateAverageEngagement(items);
      patterns.push({
        type,
        count: items.length,
        avgLikes: avgEngagement.likes,
        avgRetweets: avgEngagement.retweets,
        avgReplies: avgEngagement.replies,
        totalEngagement: avgEngagement.total,
        performance: this._ratePerformance(avgEngagement.total)
      });
    }

    // Analyze by time of day
    const timePatterns = this._analyzeTimePatterns(contentItems);
    patterns.push(...timePatterns);

    // Analyze by hashtag usage
    const hashtagPatterns = this._analyzeHashtagPatterns(contentItems);
    patterns.push(...hashtagPatterns);

    this.engagementPatterns = patterns;
    this.stateManager.set('engagement_patterns', patterns);

    return patterns;
  }

  /**
   * Find underserved topics in the niche
   * @returns {Array} Gap opportunities
   */
  async identifyNicheGaps() {
    const gaps = [];

    // Get all discovered topics
    const topics = this.discoveredTopics;

    // Get topics we've already covered in content
    const coveredTopics = this.stateManager.get('covered_topics') || [];

    // Find trending topics we haven't covered
    for (const topic of topics) {
      if (!coveredTopics.includes(topic.keyword)) {
        const gap = {
          topic: topic.keyword,
          focusArea: topic.focusArea,
          opportunity: this._assessOpportunity(topic),
          reasoning: `Trending topic not yet covered`,
          priority: this._calculatePriority(topic),
          suggestedAngles: this._suggestAngles(topic)
        };
        gaps.push(gap);
      }
    }

    // Find intersection opportunities (combinations of focus areas)
    const intersections = this._findIntersections();
    gaps.push(...intersections);

    // Sort by priority
    gaps.sort((a, b) => b.priority - a.priority);

    // Store gaps in state
    this.stateManager.set('niche_gaps', gaps);

    return gaps.slice(0, 20); // Return top 20 opportunities
  }

  /**
   * Get topics ready for content generation
   * @param {number} limit - Maximum topics to return
   * @returns {Array} Topics prioritized for content creation
   */
  getTopicsForContent(limit = 10) {
    const gaps = this.stateManager.get('niche_gaps') || [];
    const coveredTopics = this.stateManager.get('covered_topics') || [];

    // Filter out covered topics and sort by priority
    const availableTopics = gaps
      .filter(g => !coveredTopics.includes(g.topic))
      .sort((a, b) => b.priority - a.priority);

    return availableTopics.slice(0, limit);
  }

  /**
   * Mark a topic as covered
   * @param {string} topic - Topic keyword
   */
  markTopicCovered(topic) {
    const covered = this.stateManager.get('covered_topics') || [];
    if (!covered.includes(topic)) {
      covered.push(topic);
      this.stateManager.set('covered_topics', covered);
    }
  }

  /**
   * Get engagement patterns for a specific content type
   * @param {string} contentType - Type of content
   * @returns {Object|null} Pattern data
   */
  getPatternForType(contentType) {
    return this.engagementPatterns.find(p => p.type === contentType) || null;
  }

  // ===========================================
  // Helper Methods
  // ===========================================

  _extractHashtags(text) {
    const matches = text.match(/#\w+/g) || [];
    return matches.map(tag => tag.toLowerCase());
  }

  _extractKeywords(text, focusArea) {
    // Simple keyword extraction (can be enhanced with NLP)
    const stopWords = new Set(['the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
      'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
      'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought', 'used', 'to', 'of',
      'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
      'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further', 'then',
      'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
      'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
      'than', 'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because', 'until', 'while',
      'this', 'that', 'these', 'those', 'it', 'its']);

    const words = text.toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter(w => w.length > 3 && !stopWords.has(w));

    // Return unique keywords
    return [...new Set(words)];
  }

  _generateTopicId(result) {
    return `topic_${result.keyword.toLowerCase().replace(/\s+/g, '_')}_${Date.now()}`;
  }

  _mergeTopics(newTopics) {
    const existingKeywords = new Set(this.discoveredTopics.map(t => t.keyword));
    
    for (const topic of newTopics) {
      if (!existingKeywords.has(topic.keyword)) {
        this.discoveredTopics.push(topic);
        existingKeywords.add(topic.keyword);
      }
    }
  }

  _persistTopics() {
    this.stateManager.set('discovered_topics', this.discoveredTopics);
  }

  _getDefaultPatterns() {
    return [
      { type: 'thread', avgLikes: 15, avgRetweets: 5, avgReplies: 3, performance: 'good' },
      { type: 'single_tweet', avgLikes: 8, avgRetweets: 2, avgReplies: 1, performance: 'average' },
      { type: 'reply', avgLikes: 3, avgRetweets: 0.5, avgReplies: 2, performance: 'average' },
      { timing: 'morning', performance: 'good', recommendation: '9-11 AM EST' },
      { timing: 'afternoon', performance: 'average', recommendation: '2-4 PM EST' },
      { hashtag: '3-5 hashtags', performance: 'optimal' }
    ];
  }

  _groupBy(items, key) {
    return items.reduce((acc, item) => {
      const groupKey = item[key];
      if (!acc[groupKey]) acc[groupKey] = [];
      acc[groupKey].push(item);
      return acc;
    }, {});
  }

  _calculateAverageEngagement(items) {
    if (!items.length) return { likes: 0, retweets: 0, replies: 0, total: 0 };

    let totalLikes = 0, totalRetweets = 0, totalReplies = 0;

    for (const item of items) {
      const metrics = item.engagement_metrics 
        ? (typeof item.engagement_metrics === 'string' 
          ? JSON.parse(item.engagement_metrics) 
          : item.engagement_metrics)
        : {};
      totalLikes += metrics.likes || 0;
      totalRetweets += metrics.retweets || 0;
      totalReplies += metrics.replies || 0;
    }

    const total = totalLikes + totalRetweets + totalReplies;
    return {
      likes: totalLikes / items.length,
      retweets: totalRetweets / items.length,
      replies: totalReplies / items.length,
      total: total / items.length
    };
  }

  _ratePerformance(avgEngagement) {
    if (avgEngagement >= 20) return 'excellent';
    if (avgEngagement >= 10) return 'good';
    if (avgEngagement >= 5) return 'average';
    return 'low';
  }

  _analyzeTimePatterns(items) {
    const patterns = [];
    const timeSlots = {
      morning: { start: 6, end: 12, items: [], engagement: 0 },
      afternoon: { start: 12, end: 18, items: [], engagement: 0 },
      evening: { start: 18, end: 24, items: [], engagement: 0 },
      night: { start: 0, end: 6, items: [], engagement: 0 }
    };

    for (const item of items) {
      if (!item.posted_at) continue;
      const hour = new Date(item.posted_at).getHours();
      const metrics = item.engagement_metrics 
        ? (typeof item.engagement_metrics === 'string' 
          ? JSON.parse(item.engagement_metrics) 
          : item.engagement_metrics)
        : {};
      const engagement = (metrics.likes || 0) + (metrics.retweets || 0) + (metrics.replies || 0);

      for (const [slot, data] of Object.entries(timeSlots)) {
        if (hour >= data.start && hour < data.end) {
          data.items.push(item);
          data.engagement += engagement;
          break;
        }
      }
    }

    for (const [slot, data] of Object.entries(timeSlots)) {
      if (data.items.length > 0) {
        patterns.push({
          type: 'timing',
          slot,
          count: data.items.length,
          avgEngagement: data.engagement / data.items.length,
          performance: this._ratePerformance(data.engagement / data.items.length)
        });
      }
    }

    return patterns;
  }

  _analyzeHashtagPatterns(items) {
    const patterns = [];
    const hashtagCounts = { 0: [], '1-2': [], '3-5': [], '6+': [] };

    for (const item of items) {
      const content = item.content || '';
      const hashtags = (content.match(/#\w+/g) || []).length;
      const metrics = item.engagement_metrics 
        ? (typeof item.engagement_metrics === 'string' 
          ? JSON.parse(item.engagement_metrics) 
          : item.engagement_metrics)
        : {};
      const engagement = (metrics.likes || 0) + (metrics.retweets || 0) + (metrics.replies || 0);

      let category;
      if (hashtags === 0) category = '0';
      else if (hashtags <= 2) category = '1-2';
      else if (hashtags <= 5) category = '3-5';
      else category = '6+';

      hashtagCounts[category].push(engagement);
    }

    for (const [category, engagements] of Object.entries(hashtagCounts)) {
      if (engagements.length > 0) {
        const avg = engagements.reduce((a, b) => a + b, 0) / engagements.length;
        patterns.push({
          type: 'hashtag_count',
          category,
          count: engagements.length,
          avgEngagement: avg,
          performance: this._ratePerformance(avg)
        });
      }
    }

    return patterns;
  }

  _assessOpportunity(topic) {
    const volumeScore = { high: 3, medium: 2, low: 1 }[topic.volume] || 1;
    const sentimentScore = { positive: 2, neutral: 1, negative: 0 }[topic.sentiment] || 1;
    return volumeScore * sentimentScore;
  }

  _calculatePriority(topic) {
    let priority = 50; // Base priority

    // Adjust for volume
    if (topic.volume === 'high') priority += 20;
    else if (topic.volume === 'medium') priority += 10;

    // Adjust for sentiment
    if (topic.sentiment === 'positive') priority += 15;

    // Adjust for relevance to focus area
    priority += this.focusAreas.includes(topic.focusArea) ? 10 : 0;

    return Math.min(priority, 100);
  }

  _suggestAngles(topic) {
    const angles = [
      `How ${topic.keyword} relates to AI agents`,
      `${topic.keyword} best practices`,
      `Why ${topic.keyword} matters for builders`,
      `Common mistakes with ${topic.keyword}`
    ];
    return angles.slice(0, 3);
  }

  _findIntersections() {
    const intersections = [];
    
    // Find interesting combinations of focus areas
    for (let i = 0; i < this.focusAreas.length; i++) {
      for (let j = i + 1; j < this.focusAreas.length; j++) {
        const area1 = this.focusAreas[i];
        const area2 = this.focusAreas[j];
        
        intersections.push({
          topic: `${area1} + ${area2}`,
          focusArea: 'intersection',
          opportunity: 4,
          reasoning: `Unique combination of ${area1} and ${area2} content`,
          priority: 70,
          suggestedAngles: [
            `Using ${area1} for better ${area2.toLowerCase()}`,
            `The intersection of ${area1} and ${area2.toLowerCase()}`
          ]
        });
      }
    }

    return intersections;
  }
}

export default TopicsExplorer;
