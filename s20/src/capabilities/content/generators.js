/**
 * Content Generators - Functions that generate different content types
 * These functions work with the ContentFactory to produce content via LLM
 */

import { config } from '../../../config/defaults.js';
import {
  buildTweetPrompt,
  buildThreadPrompt,
  buildBlogPrompt,
  buildReplyPrompt,
  tones
} from './templates.js';

const { identity } = config;

/**
 * Maximum character limits
 */
const LIMITS = {
  TWEET: 280,
  THREAD_TWEET: 280
};

/**
 * Parse JSON response from LLM, handling potential formatting issues
 * @param {string} text - Raw response text
 * @returns {*} Parsed JSON or original text
 */
function parseResponse(text) {
  // Try direct JSON parse first
  try {
    return JSON.parse(text);
  } catch {
    // Try extracting JSON from markdown code blocks
    const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (jsonMatch) {
      try {
        return JSON.parse(jsonMatch[1].trim());
      } catch {
        // Fall through
      }
    }
    
    // Try finding array in text
    const arrayMatch = text.match(/\[[\s\S]*\]/);
    if (arrayMatch) {
      try {
        return JSON.parse(arrayMatch[0]);
      } catch {
        // Fall through
      }
    }
  }
  
  return text;
}

/**
 * Ensure content is within character limit
 * @param {string} content - Content to check
 * @param {number} limit - Character limit
 * @returns {string} Truncated content if needed
 */
function enforceLimit(content, limit) {
  if (content.length <= limit) return content;
  return content.slice(0, limit - 3) + '...';
}

/**
 * Clean up generated content
 * @param {string} content - Raw generated content
 * @returns {string} Cleaned content
 */
function cleanContent(content) {
  return content
    .replace(/^["']|["']$/g, '') // Remove surrounding quotes
    .replace(/\n{3,}/g, '\n\n') // Normalize line breaks
    .trim();
}

/**
 * Tweet Generator
 * Generates a single tweet under 280 characters
 * 
 * @param {Function} callLLM - Function to call the LLM API
 * @param {string} prompt - The topic/context for the tweet
 * @param {Object} options - Additional options
 * @returns {Promise<Object>} Generated tweet with metadata
 */
export async function tweetGenerator(callLLM, prompt, options = {}) {
  const { system, user } = buildTweetPrompt(prompt);
  
  const response = await callLLM(system, user);
  const content = cleanContent(response);
  const truncatedContent = enforceLimit(content, LIMITS.TWEET);
  
  return {
    type: 'tweet',
    content: truncatedContent,
    characterCount: truncatedContent.length,
    wasTruncated: content !== truncatedContent,
    context: prompt,
    identity: identity.handle,
    generatedAt: new Date().toISOString()
  };
}

/**
 * Thread Generator
 * Generates a connected series of tweets
 * 
 * @param {Function} callLLM - Function to call the LLM API
 * @param {string} topic - The topic for the thread
 * @param {number} count - Number of tweets in the thread
 * @param {Object} options - Additional options
 * @returns {Promise<Object>} Generated thread with metadata
 */
export async function threadGenerator(callLLM, topic, count = 5, options = {}) {
  // Ensure reasonable count
  const tweetCount = Math.min(Math.max(count, 2), 10);
  
  const { system, user } = buildThreadPrompt(topic, tweetCount);
  
  const response = await callLLM(system, user);
  const parsed = parseResponse(response);
  
  let tweets;
  if (Array.isArray(parsed)) {
    tweets = parsed;
  } else if (typeof parsed === 'string') {
    // Try to split by tweet indicators
    tweets = parsed
      .split(/(?=\d+\/)/)
      .map(t => t.replace(/^\d+\/\s*/, '').trim())
      .filter(t => t.length > 0);
  } else {
    // Fallback: treat entire response as single tweet
    tweets = [parsed];
  }
  
  // Process and validate each tweet
  const processedTweets = tweets.slice(0, tweetCount).map((tweet, index) => {
    const cleaned = cleanContent(tweet);
    return {
      index: index + 1,
      content: enforceLimit(cleaned, LIMITS.THREAD_TWEET),
      characterCount: cleaned.length
    };
  });
  
  return {
    type: 'thread',
    topic,
    tweets: processedTweets,
    totalTweets: processedTweets.length,
    identity: identity.handle,
    generatedAt: new Date().toISOString()
  };
}

/**
 * Blog Post Generator
 * Generates a structured markdown blog post
 * 
 * @param {Function} callLLM - Function to call the LLM API
 * @param {string} topic - The topic for the blog post
 * @param {Object} options - Additional options
 * @returns {Promise<Object>} Generated blog post with metadata
 */
export async function blogGenerator(callLLM, topic, options = {}) {
  const { system, user } = buildBlogPrompt(topic);
  
  const response = await callLLM(system, user, 4000); // More tokens for blog
  const content = cleanContent(response);
  
  // Extract title from first heading
  const titleMatch = content.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1] : topic;
  
  // Count words and estimate read time
  const wordCount = content.split(/\s+/).length;
  const readTimeMinutes = Math.ceil(wordCount / 200);
  
  return {
    type: 'blog',
    topic,
    title,
    content,
    wordCount,
    readTimeMinutes,
    identity: identity.handle,
    generatedAt: new Date().toISOString()
  };
}

/**
 * Reply Generator
 * Generates contextual replies to tweets
 * 
 * @param {Function} callLLM - Function to call the LLM API
 * @param {string} originalTweet - The tweet to reply to
 * @param {string} tone - The tone for the reply (helpful, curious, opinionated, excited)
 * @param {Object} options - Additional options
 * @returns {Promise<Object>} Generated reply with metadata
 */
export async function replyGenerator(callLLM, originalTweet, tone = 'helpful', options = {}) {
  // Validate tone
  const validTone = Object.keys(tones).includes(tone) ? tone : 'helpful';
  
  const { system, user } = buildReplyPrompt(originalTweet, validTone);
  
  const response = await callLLM(system, user);
  const content = cleanContent(response);
  const truncatedContent = enforceLimit(content, LIMITS.TWEET);
  
  return {
    type: 'reply',
    content: truncatedContent,
    characterCount: truncatedContent.length,
    wasTruncated: content !== truncatedContent,
    tone: validTone,
    originalTweet,
    identity: identity.handle,
    generatedAt: new Date().toISOString()
  };
}

/**
 * Content type registry for easy access
 */
export const generators = {
  tweet: tweetGenerator,
  thread: threadGenerator,
  blog: blogGenerator,
  reply: replyGenerator
};

/**
 * Get available tones
 * @returns {Object} Available tones with descriptions
 */
export function getAvailableTones() {
  return Object.entries(tones).map(([key, value]) => ({
    key,
    description: value.description
  }));
}

export default {
  tweetGenerator,
  threadGenerator,
  blogGenerator,
  replyGenerator,
  generators,
  getAvailableTones
};
