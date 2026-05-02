# AI Instructions for Code Testing and Quality Assurance

## These are instructions I must follow:

## 1. Mandatory Testing Requirements
When implementing any code, I must:
- Always run tests after implementing
- Only verify code works with real data, never mock data
- Include integration tests with actual connections
- Test with real APIs/databases, not mocked endpoints
- Ensure the application works end-to-end

## 2. Required Implementation Process
I must follow this exact sequence:
1. Implement the requested feature
2. Set up integration tests with real connections
3. Run the code manually to verify it works for the user
4. Show actual test output and workflow results
5. Continue testing until everything works perfectly

## 3. Real Data Testing Protocol
I am required to:
- Test with real database connections only
- Use actual API endpoints, never mocked ones
- Verify the application works end-to-end
- Provide manual testing steps that validate functionality
- Test with actual data flow, not sample/test data

## 4. Environment Compatibility Requirements
I must:
- Check for uv setup in the user's environment
- Check for nvm setup in the user's environment
- Verify Python version compatibility when relevant
- Use uv to install dependencies when needed
- Document specific Node.js version requirements if applicable
- Test in environment that matches the user's setup

## 5. Mandatory Error Detection and Resolution
Proactive error detection and resolution is my responsibility:

### Server/Backend Error Detection and Fixing
- **Read server logs automatically** after running tests
- **Monitor HTTP responses** and fix non-200 status codes
- **Check error logs** (`/logs/error.log`, application logs) for issues
- **Fix database connection problems** that occur during testing
- **Resolve authentication/authorization errors** found during API calls

### Browser/Frontend Error Detection and Fixing  
- **Analyze browser console errors** and fix JavaScript issues
- **Debug failed network requests** and fix API integration problems
- **Resolve CORS/security errors** that prevent proper functioning
- **Fix form validation and UI interaction problems** discovered during testing
- **Handle async operations properly** to avoid unhandled promise rejections

### Automated Error Resolution Methods
- **Log File Analysis**: Read and resolve errors found in application logs
- **Runtime Error Detection**: Fix errors that appear during test execution
- **Browser Error Monitoring**: Use available tools to detect and fix frontend issues
- **Debug Output Analysis**: Parse error messages and implement fixes
- **Iterative Testing**: Run tests, find errors, fix them, re-test automatically

### Required Problem-Solving Process
When errors occur during testing, I must:
1. **Identify the error** from logs, console, or test output
2. **Analyze the root cause** of the failure
3. **Implement the fix** in the code
4. **Re-run the test** to verify resolution
5. **Continue testing** until all errors are resolved

## 6. Mandatory Quality Assessment and Future Improvements
Beyond making it work, I must assess and document quality:

### User Experience Evaluation Requirements
- **Interface Usability**: Assess if the UI/UX is intuitive and user-friendly
- **Feature Completeness**: Identify missing functionality users would expect
- **Error Handling**: Evaluate if error messages are clear and helpful to end users
- **Performance**: Note any slow loading times or responsiveness issues
- **Accessibility**: Check basic accessibility concerns that affect user experience

### Developer Experience Evaluation Requirements  
- **Code Maintainability**: Assess code structure and readability for future development
- **Configuration Complexity**: Note if setup is too complicated for developers
- **Documentation Quality**: Identify missing or unclear documentation
- **Error Debugging**: Evaluate if errors are easy for developers to debug and fix
- **Extensibility**: Assess how easy it is to add new features or modify existing ones

### Version Improvement Tracking Requirements
I must document:
- **Current Version Issues**: Problems that need addressing in subsequent versions
- **User Pain Points**: Areas where users might struggle or get confused
- **Developer Friction**: Areas that make development harder than necessary
- **Technical Debt**: Code quality issues that could cause future problems
- **Enhancement Opportunities**: Features or improvements that would significantly upgrade the experience

### Mandatory Quality Report Format
After implementation, I must provide:
```
## Quality Assessment
### User Experience Issues Found:
- [Issue 1] - Impact: High/Medium/Low - Suggested Fix
- [Issue 2] - Impact: High/Medium/Low - Suggested Fix

### Developer Experience Issues Found:
- [Issue 1] - Impact: High/Medium/Low - Suggested Fix  
- [Issue 2] - Impact: High/Medium/Low - Suggested Fix

### Recommended Next Version Improvements:
1. [Priority 1]
2. [Priority 2]
3. [Priority 3]
```

## 7. My Core Responsibilities - I Must Follow These Requirements

### Complete Testing and Implementation Requirements
I must:
- Check for uv setup in the user's environment
- Check for nvm setup in the user's environment
- Use real API endpoints, database connections
- Test with actual data flow
- Verify manual testing workflow
- Report real connection results, not simulated ones
- Document environment requirements clearly
- **Automatically detect and fix errors found during testing**
- **Read error logs and resolve the issues they contain**
- **Continue testing until all errors are eliminated**
- **Ensure the application actually works, not just that tests pass**
- **Assess user experience and identify improvement opportunities**
- **Evaluate developer experience and note maintenance concerns**
- **Document quality issues for future version planning**
- **Prioritize improvements based on user/developer impact**

### Task Completion Criteria
I must not consider a task complete until:
1. The code works with real data and connections
2. All detected errors have been automatically fixed
3. The application functions properly in the user's environment
4. Manual testing steps have been validated
5. Quality assessment has been provided
6. Future improvement recommendations are documented

### Error Resolution Protocol
When errors occur, I must iterate until resolved:
1. Identify the error from available sources
2. Analyze the root cause
3. Implement a fix
4. Test the fix
5. Repeat until no errors remain

This document serves as my complete instruction set for ensuring working, tested, quality-assured applications.

This document serves as my complete instruction set for ensuring working, tested, quality-assured applications.
