// Cron job definitions for the agent
// Times are in cron format: minute hour day month weekday

export const schedules = [
  // Twitter monitoring
  {
    name: 'check_mentions',
    module: 'twitter',
    action: 'checkMentions',
    cron: '*/30 * * * *',  // Every 30 minutes
    enabled: true,
    description: 'Check for new mentions and replies'
  },
  {
    name: 'check_bookmarks',
    module: 'twitter',
    action: 'syncBookmarks',
    cron: '0 */2 * * *',  // Every 2 hours
    enabled: true,
    description: 'Sync bookmarks for content ideas'
  },
  {
    name: 'collect_engagement',
    module: 'twitter',
    action: 'collectEngagement',
    cron: '0 */4 * * *',  // Every 4 hours
    enabled: true,
    description: 'Collect engagement metrics for posted content'
  },

  // Content creation
  {
    name: 'generate_content',
    module: 'content',
    action: 'generateContent',
    cron: '0 9,15 * * *',  // 9am and 3pm
    enabled: true,
    description: 'Generate new content drafts'
  },
  {
    name: 'post_scheduled',
    module: 'content',
    action: 'postScheduled',
    cron: '30 * * * *',  // Every hour at :30
    enabled: true,
    description: 'Post any scheduled content due'
  },

  // Experiments
  {
    name: 'topic_exploration',
    module: 'experiments',
    action: 'exploreTopics',
    cron: '0 10 * * 1',  // Monday 10am
    enabled: true,
    description: 'Explore new topics based on trends'
  },
  {
    name: 'analyze_experiments',
    module: 'experiments',
    action: 'analyzeExperiments',
    cron: '0 18 * * 5',  // Friday 6pm
    enabled: true,
    description: 'Analyze experiment results and extract learnings'
  },

  // Maintenance
  {
    name: 'cleanup_old_data',
    module: 'system',
    action: 'cleanup',
    cron: '0 3 * * 0',  // Sunday 3am
    enabled: true,
    description: 'Clean up old logs and expired data'
  },
  {
    name: 'health_check',
    module: 'system',
    action: 'healthCheck',
    cron: '*/5 * * * *',  // Every 5 minutes
    enabled: true,
    description: 'Check system health and connectivity'
  }
];

export default schedules;
