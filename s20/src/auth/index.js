/**
 * Authentication module exports
 * Provides JWT-based authentication for multi-user support
 */

export { hash, verify } from './password.js';
export { 
  generateAccessToken, 
  generateRefreshToken, 
  verifyAccessToken,
  hashRefreshToken,
  decodeAccessToken 
} from './jwt.js';
export { authMiddleware, optionalAuth, requireTier } from './middleware.js';
export { createAuthRouter } from './routes.js';

// Default export with all components
export default {
  // Password utilities
  hash: (await import('./password.js')).hash,
  verify: (await import('./password.js')).verify,
  
  // JWT utilities
  generateAccessToken: (await import('./jwt.js')).generateAccessToken,
  generateRefreshToken: (await import('./jwt.js')).generateRefreshToken,
  verifyAccessToken: (await import('./jwt.js')).verifyAccessToken,
  
  // Middleware
  authMiddleware: (await import('./middleware.js')).authMiddleware,
  optionalAuth: (await import('./middleware.js')).optionalAuth,
  requireTier: (await import('./middleware.js')).requireTier,
  
  // Routes
  createAuthRouter: (await import('./routes.js')).createAuthRouter
};
