#!/usr/bin/env python3
"""
Budget Builder Tool - Create grant budgets with AI assistance
"""

import json
from datetime import datetime

class BudgetBuilder:
    """Build and manage grant budgets"""
    
    # Standard budget categories for federal grants
    CATEGORIES = [
        {"id": "personnel", "name": "Personnel", "description": "Salaries and wages", "required": True},
        {"id": "fringe", "name": "Fringe Benefits", "description": "Health insurance, retirement, etc.", "required": False},
        {"id": "equipment", "name": "Equipment", "description": "Items over $5,000 with useful life >1 year", "required": False},
        {"id": "supplies", "name": "Supplies", "description": "Materials, software, small equipment", "required": False},
        {"id": "travel", "name": "Travel", "description": "Domestic and international travel", "required": False},
        {"id": "consultants", "name": "Consultants/Subawards", "description": "External experts and subrecipients", "required": False},
        {"id": "other", "name": "Other Direct Costs", "description": "Publication costs, participant support", "required": False},
        {"id": "indirect", "name": "Indirect Costs", "description": "F&A costs (facilities & admin)", "required": False},
    ]
    
    # Common personnel positions
    PERSONNEL_ROLES = [
        {"role": "PI", "title": "Principal Investigator", "avg_salary": 120000, "fringe_rate": 0.30},
        {"role": "CoPI", "title": "Co-Principal Investigator", "avg_salary": 100000, "fringe_rate": 0.30},
        {"role": "PostDoc", "title": "Postdoctoral Researcher", "avg_salary": 55000, "fringe_rate": 0.30},
        {"role": "GradStudent", "title": "Graduate Student", "avg_salary": 30000, "fringe_rate": 0.15},
        {"role": "Tech", "title": "Research Technician", "avg_salary": 45000, "fringe_rate": 0.30},
        {"role": "Admin", "title": "Administrative Support", "avg_salary": 40000, "fringe_rate": 0.30},
    ]
    
    def __init__(self):
        self.budget = {
            "total_direct": 0,
            "total_indirect": 0,
            "total": 0,
            "categories": {},
            "personnel": [],
            "indirect_rate": 0.50,  # Default 50% MTDC
            "modified_total_direct_costs": 0,
        }
        
        # Initialize categories
        for cat in self.CATEGORIES:
            self.budget["categories"][cat["id"]] = {
                "amount": 0,
                "description": "",
                "items": []
            }
    
    def add_personnel(self, role, effort_months, salary=None, name=None):
        """Add personnel to budget"""
        role_info = next((r for r in self.PERSONNEL_ROLES if r["role"] == role), None)
        if not role_info:
            return {"success": False, "error": "Invalid role"}
        
        actual_salary = salary if salary else role_info["avg_salary"]
        fringe = actual_salary * role_info["fringe_rate"] * (effort_months / 12)
        
        person = {
            "role": role,
            "title": role_info["title"],
            "name": name or role_info["title"],
            "salary": actual_salary,
            "effort_months": effort_months,
            "requested": actual_salary * (effort_months / 12),
            "fringe": fringe,
            "total": actual_salary * (effort_months / 12) + fringe
        }
        
        self.budget["personnel"].append(person)
        self._recalculate()
        
        return {"success": True, "person": person}
    
    def add_category_item(self, category_id, item_name, amount, description=""):
        """Add item to a budget category"""
        if category_id not in self.budget["categories"]:
            return {"success": False, "error": "Invalid category"}
        
        item = {
            "name": item_name,
            "amount": amount,
            "description": description
        }
        
        self.budget["categories"][category_id]["items"].append(item)
        self.budget["categories"][category_id]["amount"] += amount
        self._recalculate()
        
        return {"success": True, "item": item}
    
    def set_indirect_rate(self, rate, base="mtcd"):
        """Set indirect cost rate"""
        self.budget["indirect_rate"] = rate
        self.budget["indirect_base"] = base
        self._recalculate()
    
    def _recalculate(self):
        """Recalculate budget totals"""
        # Sum personnel
        personnel_total = sum(p["total"] for p in self.budget["personnel"])
        self.budget["categories"]["personnel"]["amount"] = personnel_total
        
        # Sum all direct costs (excluding indirect)
        direct = 0
        for cat_id, cat_data in self.budget["categories"].items():
            if cat_id != "indirect":
                direct += cat_data["amount"]
        
        self.budget["total_direct"] = direct
        
        # Calculate MTDC (Modified Total Direct Costs)
        # Exclude equipment, participant support, and subawards over 25k
        mtdc = direct
        if "equipment" in self.budget["categories"]:
            mtdc -= self.budget["categories"]["equipment"]["amount"]
        if "other" in self.budget["categories"]:
            # Could exclude participant support here
            pass
        
        self.budget["modified_total_direct_costs"] = max(mtdc, 0)
        
        # Calculate indirect
        self.budget["total_indirect"] = mtdc * self.budget["indirect_rate"]
        self.budget["categories"]["indirect"]["amount"] = self.budget["total_indirect"]
        
        # Total
        self.budget["total"] = self.budget["total_direct"] + self.budget["total_indirect"]
    
    def get_budget_summary(self):
        """Get budget summary"""
        return {
            "total_direct": self.budget["total_direct"],
            "total_indirect": self.budget["total_indirect"],
            "total": self.budget["total"],
            "personnel_count": len(self.budget["personnel"]),
            "indirect_rate": self.budget["indirect_rate"],
            "categories": {k: v["amount"] for k, v in self.budget["categories"].items()}
        }
    
    def generate_budget_narrative(self):
        """Generate AI-ready budget narrative"""
        narrative = []
        
        narrative.append("## BUDGET NARRATIVE")
        narrative.append("")
        
        # Personnel
        if self.budget["personnel"]:
            narrative.append("### A. Key Personnel")
            narrative.append("")
            for p in self.budget["personnel"]:
                narrative.append(f"**{p['name']}** - {p['title']}")
                narrative.append(f"- Annual Salary: ${p['salary']:,.0f}")
                narrative.append(f"- Effort: {p['effort_months']} months ({p['effort_months']*100/12:.1f}% effort)")
                narrative.append(f"- Requested: ${p['requested']:,.0f}")
                narrative.append(f"- Fringe Benefits: ${p['fringe']:,.0f}")
                narrative.append(f"- Total: ${p['total']:,.0f}")
                narrative.append("")
        
        # Other categories
        for cat in self.CATEGORIES:
            cat_id = cat["id"]
            if cat_id == "personnel" or cat_id == "indirect":
                continue
            
            cat_data = self.budget["categories"].get(cat_id, {})
            if cat_data["amount"] > 0:
                narrative.append(f"### {cat['name']}")
                narrative.append(f"**Total: ${cat_data['amount']:,.0f}**")
                narrative.append("")
                
                for item in cat_data.get("items", []):
                    narrative.append(f"- **{item['name']}**: ${item['amount']:,.0f}")
                    if item.get("description"):
                        narrative.append(f"  - {item['description']}")
                narrative.append("")
        
        # Indirect
        narrative.append(f"### Indirect Costs (F&A)")
        narrative.append(f"Rate: {self.budget['indirect_rate']*100:.1f}%")
        narrative.append(f"Base: ${self.budget['modified_total_direct_costs']:,.0f} (MTDC)")
        narrative.append(f"Amount: ${self.budget['total_indirect']:,.0f}")
        narrative.append("")
        
        # Total
        narrative.append("## TOTAL BUDGET")
        narrative.append(f"- Direct Costs: ${self.budget['total_direct']:,.0f}")
        narrative.append(f"- Indirect Costs: ${self.budget['total_indirect']:,.0f}")
        narrative.append(f"- **TOTAL: ${self.budget['total']:,.0f}**")
        
        return "\n".join(narrative)
    
    def to_dict(self):
        """Export budget as dict"""
        return self.budget.copy()
    
    def to_json(self):
        """Export budget as JSON"""
        return json.dumps(self.budget, indent=2)
    
    @staticmethod
    def from_dict(data):
        """Load budget from dict"""
        builder = BudgetBuilder()
        builder.budget = data
        return builder
    
    @staticmethod
    def from_json(json_str):
        """Load budget from JSON"""
        data = json.loads(json_str)
        return BudgetBuilder.from_dict(data)


if __name__ == "__main__":
    # Demo
    builder = BudgetBuilder()
    
    # Add personnel
    builder.add_personnel("PI", 2, name="Dr. Jane Smith")
    builder.add_personnel("PostDoc", 12, name="Dr. John Doe")
    builder.add_personnel("GradStudent", 12)
    
    # Add other items
    builder.add_category_item("equipment", "Laboratory Equipment", 25000, "Microscope and analysis tools")
    builder.add_category_item("travel", "Conference Travel", 5000, "2 domestic conferences")
    builder.add_category_item("supplies", "Research Materials", 8000)
    
    # Set indirect rate
    builder.set_indirect_rate(0.50)
    
    print("=== Budget Summary ===")
    summary = builder.get_budget_summary()
    print(f"Total: ${summary['total']:,.0f}")
    print(f"Direct: ${summary['total_direct']:,.0f}")
    print(f"Indirect: ${summary['total_indirect']:,.0f}")
    print()
    print("=== Budget Narrative ===")
    print(builder.generate_budget_narrative())
