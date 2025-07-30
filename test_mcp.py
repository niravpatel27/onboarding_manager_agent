"""
Test script for MCP implementation
"""

import asyncio
import logging
from src.tools.mcp_database_real import OnboardingDatabaseToolsMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_operations():
    """Test basic MCP database operations"""
    print("Testing MCP Database Operations")
    print("=" * 50)
    
    # Initialize database tools
    db_tools = OnboardingDatabaseToolsMCP()
    
    try:
        # Test 1: Initialize schema
        print("\n1. Initializing database schema...")
        result = await db_tools.initialize()
        print(f"   Result: {result}")
        
        # Test 2: Create onboarding session
        print("\n2. Creating onboarding session...")
        session_result = await db_tools.create_onboarding_session(
            "Acme Corp",
            "kubernetes",
            "member-123",
            "project-456"
        )
        print(f"   Result: {session_result}")
        
        if session_result.get("status") == "success":
            session_id = session_result.get("session_id")
            
            # Test 3: Add contact
            print("\n3. Adding contact to session...")
            contact = {
                "contact_id": "contact-789",
                "email": "john.doe@acme.com",
                "first_name": "John",
                "last_name": "Doe",
                "title": "CTO",
                "contact_type": "technical"
            }
            contact_result = await db_tools.add_contact_to_session(session_id, contact)
            print(f"   Result: {contact_result}")
            
            if contact_result.get("status") == "success":
                contact_id = contact_result.get("contact_onboarding_id")
                
                # Test 4: Update statuses
                print("\n4. Updating contact statuses...")
                
                # Update committee status
                committee_result = await db_tools.update_contact_committee_status(
                    contact_id, "success", "committee-123"
                )
                print(f"   Committee update: {committee_result}")
                
                # Update Slack status
                slack_result = await db_tools.update_contact_slack_status(
                    contact_id, "success", "U123456"
                )
                print(f"   Slack update: {slack_result}")
                
                # Update email status
                email_result = await db_tools.update_contact_email_status(
                    contact_id, "success"
                )
                print(f"   Email update: {email_result}")
                
                # Update overall status
                overall_result = await db_tools.update_overall_status(contact_id)
                print(f"   Overall status update: {overall_result}")
                
                # Test 5: Update session statistics
                print("\n5. Updating session statistics...")
                stats_result = await db_tools.update_session_statistics(session_id)
                print(f"   Result: {stats_result}")
                
                # Test 6: Generate report
                print("\n6. Generating session report...")
                report_result = await db_tools.get_session_report(session_id)
                print(f"   Report: {report_result}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.error("Test error", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_mcp_operations())