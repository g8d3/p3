/**
 * Express authentication middleware
 * Provides JWT verification and user context injection
 */

import { verifyAccessToken } from './jwt.js';

/**
 * Tier hierarchy for permission checks
 */
const TIER_HIERARCHY = {
  'free': 0,
  'pro': 1,
  'enterprise': 2
};

/**
 * Middleware to require authentication
 * Verifies JWT and adds req.user
 */
export function authMiddleware(req, res, next) {
  const authHeader = req.headers.authorization;
  
  if (!authHeader) {
    return res.status(401).json({
      success: false,
      error: 'Authentication required',
      code: 'AUTH_REQUIRED'
    });
  }
  
  const [scheme, token] = authHeader.split(' ');
  
  if (scheme !== 'Bearer' || !token) {
    return res.status(401).json({
      success: false,
      error: 'Invalid authentication scheme. Use: Bearer <token>',
      code: 'INVALID_AUTH_SCHEME'
    });
  }
  
  const decoded = verifyAccessToken(token);
  
  if (!decoded) {
    return res.status(401).json({
      success: false,
      error: 'Invalid or expired token',
      code: 'INVALID_TOKEN'
    });
  }
  
  // Attach user info to request
  req.user = {
    id: decoded.userId,
    email: decoded.email,
    displayName: decoded.displayName,
    planTier: decoded.planTier
  };
  
  next();
}

/**
 * Optional authentication middleware
 * Tries to authenticate but doesn't fail if no token
 */
export function optionalAuth(req, res, next) {
  const authHeader = req.headers.authorization;
  
  if (!authHeader) {
    req.user = null;
    return next();
  }
  
  const [scheme, token] = authHeader.split(' ');
  
  if (scheme !== 'Bearer' || !token) {
    req.user = null;
    return next();
  }
  
  const decoded = verifyAccessToken(token);
  
  if (!decoded) {
    req.user = null;
    return next();
  }
  
  // Attach user info to request
  req.user = {
    id: decoded.userId,
    email: decoded.email,
    displayName: decoded.displayName,
    planTier: decoded.planTier
  };
  
  next();
}

/**
 * Middleware factory to require a minimum plan tier
 * @param {string} minTier - Minimum tier required ('free', 'pro', 'enterprise')
 * @returns {Function} Express middleware
 */
export function requireTier(minTier) {
  const minLevel = TIER_HIERARCHY[minTier] ?? 0;
  
  return (req, res, next) => {
    // Must have auth middleware run first
    if (!req.user) {
      return res.status(401).json({
        success: false,
        error: 'Authentication required',
        code: 'AUTH_REQUIRED'
      });
    }
    
    const userLevel = TIER_HIERARCHY[req.user.planTier] ?? 0;
    
    if (userLevel < minLevel) {
      return res.status(403).json({
        success: false,
        error: `This feature requires ${minTier} plan or higher`,
        code: 'INSUFFICIENT_TIER',
        currentTier: req.user.planTier,
        requiredTier: minTier
      });
    }
    
    next();
  };
}

export default {
  authMiddleware,
  optionalAuth,
  requireTier
};
