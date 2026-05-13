import sys
import os

# Add project root to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.compliance_shield import ComplianceShield

def test_masking():
    shield = ComplianceShield()
    
    test_data = [
        {
            "patient_id": 1,
            "first_name": "Pradipp",
            "last_name": "Patil",
            "dob": "1990-05-15",
            "phone": "123-456-7890",
            "email": "pradipp@example.com",
            "city": "Mumbai",
            "billing_amount": 500.50
        }
    ]
    
    masked = shield.mask_rows(test_data)
    
    print("--- ORIGINAL DATA ---")
    print(test_data[0])
    
    print("\n--- MASKED DATA ---")
    print(masked[0])
    
    # Assertions
    assert masked[0]["first_name"] == "P***p"
    assert masked[0]["dob"] == "1990-XX-XX"
    assert masked[0]["phone"] == "XXX-XXX-7890"
    assert masked[0]["email"] == "p***@example.com"
    assert masked[0]["city"] == "[MASKED LOCATION]"
    assert masked[0]["billing_amount"] == 500.50 # Numeric non-PII should be untouched
    
    print("\n✅ Masking test passed!")

if __name__ == "__main__":
    test_masking()
