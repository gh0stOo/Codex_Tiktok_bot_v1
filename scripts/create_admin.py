#!/usr/bin/env python3
"""
Skript zum Erstellen eines Admin-Users für Codex TikTok Bot.

Verwendung:
    python scripts/create_admin.py
    python scripts/create_admin.py --email admin@example.com --password securepass123 --org-name "My Org"
"""

import sys
import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "backend"))

# Setze DATABASE_URL auf localhost wenn nicht in Docker
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+psycopg2://codex:codex@localhost:5432/codex"

from app.db import SessionLocal
from app import models
from app.auth import hash_password


def create_admin_user(email: str, password: str, org_name: str = None, role: str = "owner"):
    """
    Erstellt einen Admin-User mit optionaler Organisation.
    
    Args:
        email: E-Mail-Adresse des Users
        password: Passwort des Users
        org_name: Name der Organisation (optional, wird erstellt falls nicht vorhanden)
        role: Rolle des Users in der Organisation ("owner" oder "admin")
    
    Returns:
        dict mit Informationen über erstellte/aktualisierte Objekte
    """
    db = SessionLocal()
    
    try:
        # Prüfe ob User bereits existiert
        user = db.query(models.User).filter(models.User.email == email).first()
        
        if user:
            print(f"[!] User mit E-Mail '{email}' existiert bereits. Aktualisiere Passwort...")
            user.hashed_password = hash_password(password)
            user.is_active = True
            user.email_verified = True  # Admin-User als verifiziert markieren
        else:
            print(f"[+] Erstelle neuen User: {email}")
            user = models.User(
                email=email,
                hashed_password=hash_password(password),
                is_active=True,
                email_verified=True,  # Admin-User direkt als verifiziert markieren
            )
            db.add(user)
            db.flush()  # Flush um user.id zu erhalten
        
        # Organisation erstellen/verknüpfen
        org = None
        if org_name:
            org = db.query(models.Organization).filter(models.Organization.name == org_name).first()
            
            if not org:
                print(f"[+] Erstelle neue Organisation: {org_name}")
                org = models.Organization(name=org_name)
                db.add(org)
                db.flush()
            else:
                print(f"[i] Verwende bestehende Organisation: {org_name}")
            
            # Membership prüfen/erstellen
            membership = (
                db.query(models.Membership)
                .filter(
                    models.Membership.user_id == user.id,
                    models.Membership.organization_id == org.id
                )
                .first()
            )
            
            if not membership:
                print(f"[+] Füge User als '{role}' zur Organisation hinzu...")
                membership = models.Membership(
                    user_id=user.id,
                    organization_id=org.id,
                    role=role
                )
                db.add(membership)
            else:
                # Aktualisiere Rolle falls nötig
                if membership.role != role:
                    print(f"[+] Aktualisiere Rolle von '{membership.role}' zu '{role}'...")
                    membership.role = role
                    db.add(membership)
                else:
                    print(f"[i] User ist bereits '{role}' in dieser Organisation.")
        
        db.commit()
        
        result = {
            "user_id": user.id,
            "email": user.email,
            "created": not user.id or user.id == user.id,  # Vereinfachte Prüfung
        }
        
        if org:
            result["organization_id"] = org.id
            result["organization_name"] = org.name
            result["role"] = role
        
        return result
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Fehler beim Erstellen des Admin-Users: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Erstellt einen Admin-User für Codex TikTok Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Interaktiv
  python scripts/create_admin.py
  
  # Mit allen Parametern
  python scripts/create_admin.py --email admin@example.com --password securepass123 --org-name "My Org"
  
  # Nur User ohne Organisation
  python scripts/create_admin.py --email admin@example.com --password securepass123
        """
    )
    
    parser.add_argument(
        "--email",
        type=str,
        help="E-Mail-Adresse des Admin-Users"
    )
    parser.add_argument(
        "--password",
        type=str,
        help="Passwort des Admin-Users"
    )
    parser.add_argument(
        "--org-name",
        type=str,
        help="Name der Organisation (optional)"
    )
    parser.add_argument(
        "--role",
        type=str,
        choices=["owner", "admin"],
        default="owner",
        help="Rolle des Users in der Organisation (default: owner)"
    )
    
    args = parser.parse_args()
    
    # Interaktive Eingabe falls Parameter fehlen
    email = args.email
    if not email:
        email = input("E-Mail-Adresse des Admin-Users: ").strip()
        if not email:
            print("[ERROR] E-Mail-Adresse ist erforderlich!")
            sys.exit(1)
    
    password = args.password
    if not password:
        import getpass
        password = getpass.getpass("Passwort: ").strip()
        if not password:
            print("[ERROR] Passwort ist erforderlich!")
            sys.exit(1)
        password_confirm = getpass.getpass("Passwort bestätigen: ").strip()
        if password != password_confirm:
            print("[ERROR] Passwörter stimmen nicht überein!")
            sys.exit(1)
    
    org_name = args.org_name
    if not org_name:
        org_input = input("Organisationsname (optional, Enter zum Überspringen): ").strip()
        org_name = org_input if org_input else None
    
    print("\n" + "="*60)
    print("Erstelle Admin-User...")
    print("="*60 + "\n")
    
    try:
        result = create_admin_user(email, password, org_name, args.role)
        
        print("\n" + "="*60)
        print("[SUCCESS] Admin-User erfolgreich erstellt/aktualisiert!")
        print("="*60)
        print(f"User ID: {result['user_id']}")
        print(f"E-Mail: {result['email']}")
        if 'organization_name' in result:
            print(f"Organisation: {result['organization_name']} (ID: {result['organization_id']})")
            print(f"Rolle: {result['role']}")
        print("\nDu kannst dich jetzt mit diesen Credentials einloggen:")
        print(f"  E-Mail: {email}")
        print(f"  Passwort: {'*' * len(password)}")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n[ERROR] Fehler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

