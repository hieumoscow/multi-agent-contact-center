import json
import os
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from pathlib import Path

@dataclass
class Customer:
    customerId: str
    phoneNumber: str
    name: str
    email: str
    policyNumbers: List[str]
    customerType: str
    preferredLanguage: str
    relationshipManager: str
    lastContact: str
    notes: str

class CustomerManager:
    def __init__(self):
        # Go up one level from managers to backend, then to data
        self.customers_file = Path(__file__).parent.parent / "data" / "customers.json"
        self._load_customers()

    def _load_customers(self):
        """Load customers from JSON file"""
        try:
            with open(self.customers_file, 'r') as f:
                data = json.load(f)
                self.customers = {
                    customer["phoneNumber"]: Customer(**customer)
                    for customer in data["customers"]
                }
        except Exception as e:
            print(f"Error loading customers: {str(e)}")
            self.customers = {}

    def get_customer(self, phone_number: str) -> Optional[Customer]:
        """Get customer by phone number"""
        # Normalize phone number format
        if not phone_number.startswith('+'):
            phone_number = f"+{phone_number}"
        print(f"Looking up customer with phone: {phone_number}")
        print(f"Available customers: {list(self.customers.keys())}")
        return self.customers.get(phone_number)

    def update_last_contact(self, phone_number: str):
        """Update customer's last contact date"""
        if phone_number in self.customers:
            self.customers[phone_number].lastContact = datetime.now().strftime("%Y-%m-%d")
            self._save_customers()

    def _save_customers(self):
        """Save customers to JSON file"""
        try:
            data = {
                "customers": [
                    {
                        "customerId": c.customerId,
                        "phoneNumber": c.phoneNumber,
                        "name": c.name,
                        "email": c.email,
                        "policyNumbers": c.policyNumbers,
                        "customerType": c.customerType,
                        "preferredLanguage": c.preferredLanguage,
                        "relationshipManager": c.relationshipManager,
                        "lastContact": c.lastContact,
                        "notes": c.notes
                    }
                    for c in self.customers.values()
                ]
            }
            with open(self.customers_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving customers: {str(e)}")

    def format_customer_info(self, customer: Customer) -> str:
        """Format customer information for display"""
        return f"""Customer Information:
- Name: {customer.name}
- Email: {customer.email}
- Customer Type: {customer.customerType}
- Preferred Language: {customer.preferredLanguage}
- Last Contact: {customer.lastContact}
- Notes: {customer.notes}"""
