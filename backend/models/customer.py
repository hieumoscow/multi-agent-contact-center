from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class Customer:
    customerId: str
    name: str
    type: str  # 'VIP', 'Regular', etc.
    preferences: Dict
    
    @property
    def is_vip(self) -> bool:
        """Check if customer is VIP"""
        return self.type.upper() == 'VIP'
        
    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get customer preference by key"""
        return self.preferences.get(key, default)
