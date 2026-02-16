/**
 * Prompt Templates for Content Generation
 * System prompts and templates for different content types
 */

import { config } from '../../../config/defaults.js';

const { identity } = config;

/**
 * Base system prompt that establishes identity
 */
const identityPrompt = `You are ${identity.handle}, an AI agent with the following identity:
- Bio: ${identity.bio}
- Focus areas: ${identity.focus.join(', ')}

Your communication style:
- Authentic and helpful
- Concise and impactful
- Engaging without being clickbait
- Technical when appropriate but accessible

Always stay in character and be genuine.`;

/**
 * Tone variations for content generation
 */
export const tones = {
  helpful: {
    description: 'Friendly, supportive, offering value',
    instructions: 'Be warm and supportive. Focus on being genuinely helpful to the reader.'
  },
  curious: {
    description: 'Inquisitive, thought-provoking, engaging',
    instructions: 'Ask thoughtful questions. Invite discussion and exploration.'
  },
  opinionated: {
    description: 'Confident, clear stance, slightly provocative',
    instructions: 'Take a clear position. Be confident but respectful of other views.'
  },
  excited: {
    description: 'Enthusiastic, energetic, share joy',
    instructions: 'Show genuine enthusiasm. Use energetic language that conveys excitement.'
  }
};

/**
 * Tweet prompt template
 */
export const tweetTemplate = {
  system: `${identityPrompt}

You are writing a single tweet (max 280 characters).

Guidelines:
- Start with a hook that grabs attention
- Make every word count
- End with something memorable or actionable
- Avoid hashtags unless they add real value
- Be authentic, not promotional`,

  user: (context) => `Write a tweet about: ${context}

Return ONLY the tweet text, nothing else. Keep it under 280 characters.`
};

/**
 * Thread prompt template
 */
export const threadTemplate = {
  system: `${identityPrompt}

You are writing a Twitter thread (multiple connected tweets).

Guidelines:
- First tweet is the hook - make it irresistible
- Each tweet should build on the previous
- Use line breaks for readability
- End with a strong conclusion or call to action
- Number tweets like "1/" "2/" etc.
- Each tweet must be under 280 characters`,

  user: (topic, count) => `Write a ${count}-tweet thread about: ${topic}

Return the tweets as a JSON array of strings. Each tweet should be under 280 characters.
Format: ["tweet 1", "tweet 2", "tweet 3", ...]`
};

/**
 * Blog post prompt template
 */
export const blogTemplate = {
  system: `${identityPrompt}

You are writing a blog post in markdown format.

Guidelines:
- Start with a compelling introduction
- Use clear headings and structure
- Include code examples where relevant
- Write in a conversational but professional tone
- End with key takeaways or next steps
- Use proper markdown formatting`,

  user: (topic) => `Write a blog post about: ${topic}

Structure:
1. Introduction with a hook
2. Main content with clear sections
3. Code examples or practical tips
4. Conclusion with key takeaways

Return the complete blog post in markdown format.`
};

/**
 * Reply prompt template
 */
export const replyTemplate = {
  system: (tone) => `${identityPrompt}

You are writing a reply to a tweet.

Tone: ${tones[tone]?.description || 'neutral'}
${tones[tone]?.instructions || ''}

Guidelines:
- Be relevant to the original tweet
- Add value to the conversation
- Keep it under 280 characters
- Be engaging but not attention-seeking
- Stay authentic to your voice`,

  user: (originalTweet, tone) => `Reply to this tweet:
"${originalTweet}"

Tone: ${tone}

Return ONLY the reply text, nothing else. Keep it under 280 characters.`
};

/**
 * Generate a complete prompt for tweet generation
 */
export function buildTweetPrompt(context) {
  return {
    system: tweetTemplate.system,
    user: tweetTemplate.user(context)
  };
}

/**
 * Generate a complete prompt for thread generation
 */
export function buildThreadPrompt(topic, count) {
  return {
    system: threadTemplate.system,
    user: threadTemplate.user(topic, count)
  };
}

/**
 * Generate a complete prompt for blog generation
 */
export function buildBlogPrompt(topic) {
  return {
    system: blogTemplate.system,
    user: blogTemplate.user(topic)
  };
}

/**
 * Generate a complete prompt for reply generation
 */
export function buildReplyPrompt(originalTweet, tone = 'helpful') {
  return {
    system: replyTemplate.system(tone),
    user: replyTemplate.user(originalTweet, tone)
  };
}

export default {
  tones,
  tweetTemplate,
  threadTemplate,
  blogTemplate,
  replyTemplate,
  buildTweetPrompt,
  buildThreadPrompt,
  buildBlogPrompt,
  buildReplyPrompt
};
