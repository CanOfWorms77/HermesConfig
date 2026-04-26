---
name: debug-api-integration-auth-issues
description: A reusable approach for troubleshooting when API endpoints appear reachable but return ineffective responses regardless of authentication credentials.
---
This skill provides a systematic approach for debugging API integration issues where endpoints return success indicators but with ineffective responses, particularly when authentication problems are suspected.

## When to Use This Skill
- API endpoints return success: true but with empty or minimal response bodies
- Authentication issues persist despite trying different key values (valid, invalid, or none)
- Need to distinguish between network connectivity problems and API execution issues  
- Verifying that request formatting matches service documentation exactly
- Testing multiple endpoints from the same service to isolate the problem

## How to Apply This Approach
1. **Test endpoint reachability** using browser tools (GET requests) to confirm basic connectivity
2. **Experiment with authentication methods**:
   - No authorization header
   - Valid API key (when available)
   - Invalid or test API key
   - Missing authorization header entirely
3. **Verify tool functionality** with known-working external APIs (e.g., httpbin.org) to confirm your request construction tools are working properly
4. **Check for service-wide issues** by testing multiple endpoints from the same service provider
5. **Validate request construction** against the service's official API documentation, paying close attention to:
   - HTTP method (GET, POST, etc.)
   - Required headers (Content-Type, Authorization, etc.)
   - Request body structure and required fields
   - Query parameters if applicable

## Expected Outcomes and Diagnostics
- Determine whether the issue is authentication-specific (works with valid key) or service-wide (fails regardless of credentials)
- Establish if new credentials are required from the service provider
- Confirm whether your request construction matches specifications
- Document specific findings for future reference and troubleshooting similar issues
- If using in an agent context, consider whether environment-specific factors might be interfering

## Reusability Notes
This approach is reusable for similar API integration debugging scenarios involving:
- Authentication problems with otherwise reachable endpoints
- Services returning consistent ineffective responses regardless of provided credentials
- Situations requiring distinction between network-level and application-level issues
- Cases where request formatting validation against documentation is necessary

This skill is particularly valuable for agent-based systems that need to integrate with external APIs for capabilities like web search, where authentication issues can silently prevent functionality despite apparent connectivity.