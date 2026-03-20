#!/usr/bin/env python3
"""
Grant Writing CLI Tool
Command-line interface for the grant writing system
"""

import argparse
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from grant_db import init_db, add_client, add_grant, save_draft, create_invoice, get_client, list_clients, update_client_status

def cmd_init(args):
    """Initialize the grant system database"""
    init_db()
    print("✓ Grant system database initialized")

def cmd_new_client(args):
    """Create a new client"""
    client_id = add_client(args.org, args.contact, args.email)
    print(f"✓ Created client: {client_id}")
    
    # Create initial invoice for prep fee
    if args.prep_fee:
        inv_id = create_invoice(client_id, 'preparation', 99)
        print(f"✓ Created prep fee invoice: {inv_id}")

def cmd_list_clients(args):
    """List all clients"""
    clients = list_clients(args.status)
    if not clients:
        print("No clients found")
        return
    
    for c in clients:
        print(f"{c['id']} | {c['organization_name']} | {c['contact_name']} | {c['status']} | {c['current_stage']}")

def cmd_client_info(args):
    """Show detailed client info"""
    client = get_client(args.client_id)
    if not client:
        print(f"Client {args.client_id} not found")
        return
    
    print(f"\n=== {client['organization_name']} ===")
    print(f"Contact: {client['contact_name']} ({client['contact_email']})")
    print(f"Status: {client['status']} | Stage: {client['current_stage']}")
    print(f"Created: {client['created_at']}")
    print(f"Updated: {client['updated_at']}")
    
    if client.get('intake_data'):
        try:
            intake = json.loads(client['intake_data'])
            print(f"\nIntake Data:")
            for k, v in intake.items():
                if v:
                    print(f"  {k}: {v}")
        except:
            pass

def cmd_assign_grant(args):
    """Assign a grant to a client"""
    # Load grant from database
    grants_db = Path.home() / ".hermes" / "grant-system" / "research" / "iot_grants_db.json"
    if grants_db.exists():
        with open(grants_db) as f:
            grants_data = json.load(f)
            grant_info = None
            for g in grants_data.get('grants', []):
                if g['id'] == args.grant_id:
                    grant_info = g
                    break
            
            if grant_info:
                grant_id = add_grant(args.client_id, grant_info)
                print(f"✓ Assigned grant {grant_info['name']} to client")
                print(f"  Grant ID: {grant_id}")
                print(f"  Agency: {grant_info['agency']}")
                print(f"  Amount: ${grant_info['amount_min']:,} - ${grant_info['amount_max']:,}")
                print(f"  Deadline: {grant_info['deadline']}")
            else:
                print(f"Grant {args.grant_id} not found in database")
    else:
        print("Grant database not found")

def cmd_write_section(args):
    """Write a grant section"""
    print(f"Writing section: {args.section}")
    print(f"Grant: {args.grant_id}")
    print(f"Client: {args.client_id}")
    print("\nThis would invoke the LLM to write the section.")
    print("Use the interactive mode for AI-assisted writing.")

def cmd_invoice(args):
    """Create an invoice"""
    inv_id = create_invoice(args.client_id, args.type, args.amount)
    print(f"✓ Created invoice: {inv_id}")
    print(f"  Type: {args.type}")
    print(f"  Amount: ${args.amount}")
    print(f"  Status: pending")

def main():
    parser = argparse.ArgumentParser(description='Grant Writing System CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # init
    subparsers.add_parser('init', help='Initialize database')
    
    # new-client
    new_client = subparsers.add_parser('new-client', help='Create new client')
    new_client.add_argument('--org', required=True, help='Organization name')
    new_client.add_argument('--contact', required=True, help='Contact name')
    new_client.add_argument('--email', required=True, help='Contact email')
    new_client.add_argument('--prep-fee', action='store_true', help='Create prep fee invoice')
    
    # list
    list_clients = subparsers.add_parser('list', help='List clients')
    list_clients.add_argument('--status', help='Filter by status')
    
    # info
    info = subparsers.add_parser('info', help='Show client info')
    info.add_argument('client_id', help='Client ID')
    
    # assign-grant
    assign = subparsers.add_parser('assign-grant', help='Assign grant to client')
    assign.add_argument('client_id', help='Client ID')
    assign.add_argument('grant_id', help='Grant ID')
    
    # write-section
    write = subparsers.add_parser('write-section', help='Write grant section')
    write.add_argument('client_id', help='Client ID')
    write.add_argument('grant_id', help='Grant ID')
    write.add_argument('section', help='Section name')
    
    # invoice
    invoice = subparsers.add_parser('invoice', help='Create invoice')
    invoice.add_argument('client_id', help='Client ID')
    invoice.add_argument('type', choices=['preparation', 'success_under_1m', 'success_over_1m'], help='Invoice type')
    invoice.add_argument('amount', type=float, help='Amount')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    commands = {
        'init': cmd_init,
        'new-client': cmd_new_client,
        'list': cmd_list_clients,
        'info': cmd_client_info,
        'assign-grant': cmd_assign_grant,
        'write-section': cmd_write_section,
        'invoice': cmd_invoice,
    }
    
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
