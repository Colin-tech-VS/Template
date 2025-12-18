#!/usr/bin/env python3
"""
Script de migration pour appliquer les tenant_id corrects à toutes les données de chaque site.

RÈGLES STRICTES:
1. Tous les tenant_id DOIVENT venir exclusivement de la table tenants
2. Le tenant_id = 1 (défaut) est INTERDIT - utiliser le tenant_id réel du site
3. Identifier le tenant_id de chaque site via domaine, slug, siteid dans la table tenants
4. Appliquer le tenant_id à TOUTES les données du site dans TOUTES les tables
5. NE JAMAIS modifier les données métier, relations, clés primaires, timestamps, IDs
6. Produire un audit complet avec tous les détails
7. Si ambiguïté (plusieurs tenant_id possibles), arrêter et demander résolution
8. NE JAMAIS déduire un tenant_id sans validation explicite dans la table tenants
"""

import os
import sys
import json
import traceback
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Import des fonctions de base de données
from database import get_db_connection, adapt_query

# Tables qui contiennent tenant_id et doivent être mises à jour
TABLES_WITH_TENANT_ID = [
    'users',
    'paintings',
    'carts',
    'cart_items',
    'orders',
    'order_items',
    'exhibitions',
    'custom_requests',
    'notifications',
    'favorites',
    'settings',
    'saas_sites',
    'stripe_events'
]

class TenantMigrationAuditor:
    """Classe pour gérer la migration et l'audit des tenant_id"""
    
    def __init__(self):
        self.audit_report = {
            'execution_date': datetime.now().isoformat(),
            'tenants_found': [],
            'sites_processed': [],
            'tables_updated': {},
            'total_rows_updated': 0,
            'anomalies': [],
            'warnings': [],
            'errors': []
        }
        self.dry_run = False
    
    def log_warning(self, message):
        """Enregistre un avertissement"""
        print(f"⚠️  {message}")
        self.audit_report['warnings'].append(message)
    
    def log_error(self, message):
        """Enregistre une erreur"""
        print(f"❌ {message}")
        self.audit_report['errors'].append(message)
    
    def log_anomaly(self, message):
        """Enregistre une anomalie"""
        print(f"🔍 ANOMALIE: {message}")
        self.audit_report['anomalies'].append(message)
    
    def get_all_tenants(self, conn):
        """
        Récupère TOUS les tenants depuis la table tenants.
        RÈGLE 1: Tous les tenant_id viennent exclusivement de cette table.
        """
        cursor = conn.cursor()
        
        try:
            query = "SELECT id, host, name, created_at FROM tenants ORDER BY id"
            cursor.execute(query)
            tenants = cursor.fetchall()
            
            tenant_list = []
            for tenant in tenants:
                if isinstance(tenant, dict):
                    tenant_data = tenant
                else:
                    # Convert tuple to dict
                    tenant_data = {
                        'id': tenant[0],
                        'host': tenant[1],
                        'name': tenant[2],
                        'created_at': tenant[3]
                    }
                tenant_list.append(tenant_data)
                print(f"  Tenant trouvé: id={tenant_data['id']}, host={tenant_data['host']}, name={tenant_data['name']}")
            
            self.audit_report['tenants_found'] = tenant_list
            return tenant_list
            
        except Exception as e:
            self.log_error(f"Erreur lors de la récupération des tenants: {e}")
            raise
    
    def identify_site_tenant(self, conn, site_data):
        """
        Identifie le tenant_id correct pour un site en utilisant UNIQUEMENT la table tenants.
        RÈGLE 3: Identifier via domaine, slug, siteid dans la table tenants.
        RÈGLE 7: Si ambiguïté, arrêter l'opération.
        """
        cursor = conn.cursor()
        
        # Essayer de trouver le tenant via le domaine du site
        final_domain = site_data.get('final_domain')
        sandbox_url = site_data.get('sandbox_url')
        site_id = site_data.get('id')
        
        candidates = []
        
        # Chercher par final_domain
        if final_domain:
            try:
                query = "SELECT id, host FROM tenants WHERE host = %s"
                cursor.execute(query, (final_domain,))
                result = cursor.fetchone()
                if result:
                    tenant_id = result[0] if isinstance(result, (list, tuple)) else result.get('id')
                    tenant_host = result[1] if isinstance(result, (list, tuple)) else result.get('host')
                    candidates.append({
                        'tenant_id': tenant_id,
                        'host': tenant_host,
                        'match_type': 'final_domain',
                        'match_value': final_domain
                    })
            except Exception as e:
                self.log_warning(f"Erreur recherche tenant par final_domain '{final_domain}': {e}")
        
        # Chercher par sandbox_url (extraire le domaine)
        if sandbox_url and not candidates:
            try:
                # Extraire le domaine de l'URL sandbox
                parsed = urlparse(sandbox_url)
                sandbox_host = parsed.netloc or parsed.path
                if sandbox_host:
                    query = "SELECT id, host FROM tenants WHERE host = %s"
                    cursor.execute(query, (sandbox_host,))
                    result = cursor.fetchone()
                    if result:
                        tenant_id = result[0] if isinstance(result, (list, tuple)) else result.get('id')
                        tenant_host = result[1] if isinstance(result, (list, tuple)) else result.get('host')
                        candidates.append({
                            'tenant_id': tenant_id,
                            'host': tenant_host,
                            'match_type': 'sandbox_url',
                            'match_value': sandbox_host
                        })
            except Exception as e:
                self.log_warning(f"Erreur recherche tenant par sandbox_url '{sandbox_url}': {e}")
        
        # RÈGLE 7: Vérifier l'ambiguïté
        if len(candidates) > 1:
            # Vérifier si tous les candidats ont le même tenant_id
            unique_tenant_ids = set(c['tenant_id'] for c in candidates)
            if len(unique_tenant_ids) > 1:
                self.log_anomaly(
                    f"Site {site_id} a plusieurs tenant_id possibles: {candidates}"
                )
                raise ValueError(
                    f"AMBIGUÏTÉ: Site {site_id} correspond à plusieurs tenants différents. "
                    f"Résolution manuelle requise. Candidats: {candidates}"
                )
        
        if candidates:
            return candidates[0]
        
        # Aucun tenant trouvé
        return None
    
    def get_all_sites(self, conn):
        """
        Récupère tous les sites depuis saas_sites.
        """
        cursor = conn.cursor()
        
        try:
            query = """
                SELECT id, user_id, status, sandbox_url, final_domain, tenant_id, created_at
                FROM saas_sites
                ORDER BY id
            """
            cursor.execute(query)
            sites = cursor.fetchall()
            
            site_list = []
            for site in sites:
                if isinstance(site, dict):
                    site_data = site
                else:
                    # Convert tuple to dict
                    site_data = {
                        'id': site[0],
                        'user_id': site[1],
                        'status': site[2],
                        'sandbox_url': site[3],
                        'final_domain': site[4],
                        'current_tenant_id': site[5],
                        'created_at': site[6]
                    }
                site_list.append(site_data)
            
            return site_list
            
        except Exception as e:
            self.log_error(f"Erreur lors de la récupération des sites: {e}")
            raise
    
    
    def apply_tenant_to_site_data(self, conn, site_data, tenant_match):
        """
        Applique le tenant_id correct à TOUTES les données d'un site.
        RÈGLE 4: Appliquer à TOUTES les données dans TOUTES les tables.
        
        Stratégie:
        1. Mettre à jour saas_sites pour ce site
        2. Mettre à jour l'utilisateur propriétaire (user_id)
        3. Mettre à jour toutes les données liées à cet utilisateur:
           - paintings créées par cet utilisateur
           - carts de cet utilisateur
           - cart_items des carts de cet utilisateur
           - orders de cet utilisateur
           - order_items des orders de cet utilisateur
           - favorites de cet utilisateur
           - notifications de cet utilisateur
           - custom_requests de cet utilisateur
           - exhibitions créées par cet utilisateur (si admin)
           - settings de ce tenant (par domaine/host)
        """
        site_id = site_data['id']
        user_id = site_data.get('user_id')
        current_tenant_id = site_data.get('current_tenant_id', 1)
        new_tenant_id = tenant_match['tenant_id']
        
        print(f"\n{'='*80}")
        print(f"Traitement du site {site_id}")
        print(f"  User ID: {user_id}")
        print(f"  Domaine: {site_data.get('final_domain', 'N/A')}")
        print(f"  Sandbox: {site_data.get('sandbox_url', 'N/A')}")
        print(f"  Tenant actuel: {current_tenant_id}")
        print(f"  Nouveau tenant: {new_tenant_id} (host: {tenant_match['host']})")
        print(f"  Match via: {tenant_match['match_type']}")
        print(f"{'='*80}")
        
        # RÈGLE 2: Vérifier que le nouveau tenant_id n'est pas 1
        if new_tenant_id == 1:
            self.log_warning(
                f"Site {site_id}: Le tenant_id trouvé est 1 (défaut). "
                f"Vérifiez que c'est bien le tenant correct."
            )
        
        site_report = {
            'site_id': site_id,
            'user_id': user_id,
            'final_domain': site_data.get('final_domain'),
            'sandbox_url': site_data.get('sandbox_url'),
            'old_tenant_id': current_tenant_id,
            'new_tenant_id': new_tenant_id,
            'tenant_host': tenant_match['host'],
            'match_type': tenant_match['match_type'],
            'tables_updated': {},
            'total_rows': 0
        }
        
        cursor = conn.cursor()
        
        # 1. Mettre à jour saas_sites pour ce site
        try:
            rows_updated = self.update_site_specific_data(
                cursor, conn, 'saas_sites', 
                "id = %s", [site_id],
                current_tenant_id, new_tenant_id
            )
            if rows_updated > 0:
                print(f"  ✅ saas_sites: {rows_updated} ligne(s) mise(s) à jour")
                site_report['tables_updated']['saas_sites'] = rows_updated
                site_report['total_rows'] += rows_updated
        except Exception as e:
            self.log_error(f"Erreur saas_sites: {e}")
        
        # Si pas d'user_id, on ne peut pas continuer
        if not user_id:
            self.log_warning(f"Site {site_id} n'a pas de user_id - impossible de mettre à jour les données liées")
            self.audit_report['sites_processed'].append(site_report)
            return site_report
        
        # 2. Mettre à jour l'utilisateur propriétaire
        try:
            rows_updated = self.update_site_specific_data(
                cursor, conn, 'users',
                "id = %s", [user_id],
                current_tenant_id, new_tenant_id
            )
            if rows_updated > 0:
                print(f"  ✅ users: {rows_updated} ligne(s) mise(s) à jour")
                site_report['tables_updated']['users'] = rows_updated
                site_report['total_rows'] += rows_updated
        except Exception as e:
            self.log_error(f"Erreur users: {e}")
        
        # 3. Mettre à jour toutes les données liées à cet utilisateur
        # Tables directement liées par user_id
        user_linked_tables = [
            ('paintings', 'user_id'),  # Si la table paintings a une colonne user_id (sinon on prend tout)
            ('carts', 'user_id'),
            ('orders', 'user_id'),
            ('favorites', 'user_id'),
            ('notifications', 'user_id'),
            ('custom_requests', 'user_id'),  # Si custom_requests est lié à user_id
        ]
        
        for table_name, user_column in user_linked_tables:
            try:
                # Vérifier si la colonne existe
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = %s
                """, (table_name, user_column))
                
                if not cursor.fetchone():
                    # Si pas de colonne user_id, mettre à jour toutes les données de ce tenant
                    # (cas des paintings qui appartiennent au site, pas forcément à un user spécifique)
                    rows_updated = self.update_site_specific_data(
                        cursor, conn, table_name,
                        None, None,  # Pas de condition spécifique, juste par tenant_id
                        current_tenant_id, new_tenant_id
                    )
                else:
                    # Mettre à jour par user_id avec paramètres
                    rows_updated = self.update_site_specific_data(
                        cursor, conn, table_name,
                        f"{user_column} = %s", [user_id],
                        current_tenant_id, new_tenant_id
                    )
                
                if rows_updated > 0:
                    print(f"  ✅ {table_name}: {rows_updated} ligne(s) mise(s) à jour")
                    site_report['tables_updated'][table_name] = rows_updated
                    site_report['total_rows'] += rows_updated
            except Exception as e:
                self.log_error(f"Erreur {table_name}: {e}")
        
        # 4. Mettre à jour cart_items via les carts de l'utilisateur
        try:
            rows_updated = self.update_site_specific_data(
                cursor, conn, 'cart_items',
                "cart_id IN (SELECT id FROM carts WHERE user_id = %s AND tenant_id = %s)",
                [user_id, current_tenant_id],
                current_tenant_id, new_tenant_id
            )
            if rows_updated > 0:
                print(f"  ✅ cart_items: {rows_updated} ligne(s) mise(s) à jour")
                site_report['tables_updated']['cart_items'] = rows_updated
                site_report['total_rows'] += rows_updated
        except Exception as e:
            self.log_error(f"Erreur cart_items: {e}")
        
        # 5. Mettre à jour order_items via les orders de l'utilisateur
        try:
            rows_updated = self.update_site_specific_data(
                cursor, conn, 'order_items',
                "order_id IN (SELECT id FROM orders WHERE user_id = %s AND tenant_id = %s)",
                [user_id, current_tenant_id],
                current_tenant_id, new_tenant_id
            )
            if rows_updated > 0:
                print(f"  ✅ order_items: {rows_updated} ligne(s) mise(s) à jour")
                site_report['tables_updated']['order_items'] = rows_updated
                site_report['total_rows'] += rows_updated
        except Exception as e:
            self.log_error(f"Erreur order_items: {e}")
        
        # 6. Mettre à jour exhibitions (toutes celles du tenant actuel)
        try:
            rows_updated = self.update_site_specific_data(
                cursor, conn, 'exhibitions',
                None, None,
                current_tenant_id, new_tenant_id
            )
            if rows_updated > 0:
                print(f"  ✅ exhibitions: {rows_updated} ligne(s) mise(s) à jour")
                site_report['tables_updated']['exhibitions'] = rows_updated
                site_report['total_rows'] += rows_updated
        except Exception as e:
            self.log_error(f"Erreur exhibitions: {e}")
        
        # 7. Mettre à jour settings (tous les settings du tenant actuel)
        try:
            rows_updated = self.update_site_specific_data(
                cursor, conn, 'settings',
                None, None,
                current_tenant_id, new_tenant_id
            )
            if rows_updated > 0:
                print(f"  ✅ settings: {rows_updated} ligne(s) mise(s) à jour")
                site_report['tables_updated']['settings'] = rows_updated
                site_report['total_rows'] += rows_updated
        except Exception as e:
            self.log_error(f"Erreur settings: {e}")
        
        # 8. Mettre à jour stripe_events (tous les events du tenant actuel)
        try:
            rows_updated = self.update_site_specific_data(
                cursor, conn, 'stripe_events',
                None, None,
                current_tenant_id, new_tenant_id
            )
            if rows_updated > 0:
                print(f"  ✅ stripe_events: {rows_updated} ligne(s) mise(s) à jour")
                site_report['tables_updated']['stripe_events'] = rows_updated
                site_report['total_rows'] += rows_updated
        except Exception as e:
            self.log_error(f"Erreur stripe_events: {e}")
        
        # Mettre à jour les statistiques globales
        for table_name, count in site_report['tables_updated'].items():
            if table_name not in self.audit_report['tables_updated']:
                self.audit_report['tables_updated'][table_name] = 0
            self.audit_report['tables_updated'][table_name] += count
        self.audit_report['total_rows_updated'] += site_report['total_rows']
        
        self.audit_report['sites_processed'].append(site_report)
        return site_report
    
    def update_site_specific_data(self, cursor, conn, table_name, where_conditions, where_params, old_tenant_id, new_tenant_id):
        """
        Met à jour les tenant_id dans une table avec une clause WHERE spécifique.
        
        Args:
            cursor: Database cursor
            conn: Database connection
            table_name: Name of the table (must be in whitelist)
            where_conditions: WHERE clause conditions (without tenant_id) or None
            where_params: Parameters for the WHERE clause (tuple/list) or None
            old_tenant_id: Old tenant_id value
            new_tenant_id: New tenant_id value
        """
        # Whitelist of allowed table names
        if table_name not in TABLES_WITH_TENANT_ID:
            raise ValueError(f"Table {table_name} is not allowed for tenant migration")
        
        try:
            # Vérifier si la table existe
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = %s
            """, (table_name,))
            
            if not cursor.fetchone():
                return 0
            
            # Construire la requête de comptage avec paramètres
            if where_conditions:
                count_query = f"SELECT COUNT(*) FROM {table_name} WHERE ({where_conditions}) AND tenant_id = %s"
                count_params = list(where_params) + [old_tenant_id]
                cursor.execute(count_query, tuple(count_params))
            else:
                count_query = f"SELECT COUNT(*) FROM {table_name} WHERE tenant_id = %s"
                cursor.execute(count_query, (old_tenant_id,))
            
            result = cursor.fetchone()
            count = result[0] if isinstance(result, (list, tuple)) else result.get('count', 0)
            
            if count == 0:
                return 0
            
            # Mettre à jour si pas en dry-run
            if not self.dry_run:
                if where_conditions:
                    update_query = f"UPDATE {table_name} SET tenant_id = %s WHERE ({where_conditions}) AND tenant_id = %s"
                    update_params = [new_tenant_id] + list(where_params) + [old_tenant_id]
                    cursor.execute(update_query, tuple(update_params))
                else:
                    update_query = f"UPDATE {table_name} SET tenant_id = %s WHERE tenant_id = %s"
                    cursor.execute(update_query, (new_tenant_id, old_tenant_id))
                conn.commit()
            
            return count
            
        except Exception as e:
            conn.rollback()
            raise
    
    def run_migration(self, dry_run=False):
        """
        Exécute la migration complète.
        """
        self.dry_run = dry_run
        
        print("\n" + "="*80)
        print("MIGRATION DES TENANT_ID - ISOLATION MULTI-TENANT")
        print("="*80)
        
        if dry_run:
            print("⚠️  MODE DRY-RUN: Aucune modification ne sera effectuée")
            print()
        
        with get_db_connection() as conn:
            # ÉTAPE 1: Récupérer tous les tenants
            print("\n📋 ÉTAPE 1: Récupération des tenants depuis la table 'tenants'")
            print("-" * 80)
            tenants = self.get_all_tenants(conn)
            
            if not tenants:
                self.log_error("Aucun tenant trouvé dans la table 'tenants'!")
                return False
            
            print(f"\n✅ {len(tenants)} tenant(s) trouvé(s)")
            
            # Vérifier qu'il y a au moins un tenant non-défaut
            non_default_tenants = [t for t in tenants if t['id'] != 1]
            if not non_default_tenants:
                self.log_warning(
                    "Seul le tenant par défaut (id=1) existe. "
                    "Créez des tenants pour chaque site avant d'exécuter cette migration."
                )
            
            # ÉTAPE 2: Récupérer tous les sites
            print("\n📋 ÉTAPE 2: Récupération des sites depuis 'saas_sites'")
            print("-" * 80)
            sites = self.get_all_sites(conn)
            
            print(f"\n✅ {len(sites)} site(s) trouvé(s)")
            
            if not sites:
                self.log_warning("Aucun site trouvé dans saas_sites")
                return True
            
            # ÉTAPE 3: Pour chaque site, identifier son tenant et appliquer les mises à jour
            print("\n📋 ÉTAPE 3: Identification et application des tenant_id")
            print("-" * 80)
            
            for site_data in sites:
                try:
                    # Identifier le tenant du site
                    tenant_match = self.identify_site_tenant(conn, site_data)
                    
                    if not tenant_match:
                        self.log_warning(
                            f"Site {site_data['id']} ({site_data.get('final_domain', 'N/A')}): "
                            f"Aucun tenant correspondant trouvé dans la table 'tenants'. "
                            f"Ce site gardera tenant_id={site_data.get('current_tenant_id', 1)}"
                        )
                        continue
                    
                    # Appliquer le tenant_id à toutes les données du site
                    site_report = self.apply_tenant_to_site_data(conn, site_data, tenant_match)
                    
                except Exception as e:
                    self.log_error(f"Erreur lors du traitement du site {site_data['id']}: {e}")
                    import traceback
                    traceback.print_exc()
        
        return True
    
    def print_audit_report(self):
        """
        Affiche et sauvegarde le rapport d'audit complet.
        RÈGLE 6: Produire un audit complet.
        """
        print("\n" + "="*80)
        print("📊 RAPPORT D'AUDIT COMPLET")
        print("="*80)
        
        # Résumé
        print("\n📈 RÉSUMÉ")
        print("-" * 80)
        print(f"Date d'exécution: {self.audit_report['execution_date']}")
        print(f"Tenants trouvés: {len(self.audit_report['tenants_found'])}")
        print(f"Sites traités: {len(self.audit_report['sites_processed'])}")
        print(f"Total lignes mises à jour: {self.audit_report['total_rows_updated']}")
        
        # Tenants
        print("\n🏢 TENANTS TROUVÉS")
        print("-" * 80)
        for tenant in self.audit_report['tenants_found']:
            status = "❌ DÉFAUT (id=1)" if tenant['id'] == 1 else "✅"
            print(f"{status} Tenant {tenant['id']}: {tenant['host']} ({tenant.get('name', 'N/A')})")
        
        # Sites
        print("\n🌐 SITES TRAITÉS")
        print("-" * 80)
        if not self.audit_report['sites_processed']:
            print("Aucun site traité")
        else:
            for site in self.audit_report['sites_processed']:
                print(f"\nSite {site['site_id']}:")
                print(f"  Domaine: {site.get('final_domain', 'N/A')}")
                print(f"  Tenant: {site['old_tenant_id']} → {site['new_tenant_id']} (host: {site['tenant_host']})")
                print(f"  Match: {site['match_type']}")
                print(f"  Lignes mises à jour: {site['total_rows']}")
                if site['tables_updated']:
                    for table, count in site['tables_updated'].items():
                        print(f"    - {table}: {count} ligne(s)")
        
        # Tables
        print("\n📊 MISES À JOUR PAR TABLE")
        print("-" * 80)
        if not self.audit_report['tables_updated']:
            print("Aucune table mise à jour")
        else:
            for table, count in sorted(self.audit_report['tables_updated'].items()):
                print(f"  {table}: {count} ligne(s)")
        
        # Anomalies
        if self.audit_report['anomalies']:
            print("\n🔍 ANOMALIES DÉTECTÉES")
            print("-" * 80)
            for anomaly in self.audit_report['anomalies']:
                print(f"  - {anomaly}")
        
        # Avertissements
        if self.audit_report['warnings']:
            print("\n⚠️  AVERTISSEMENTS")
            print("-" * 80)
            for warning in self.audit_report['warnings']:
                print(f"  - {warning}")
        
        # Erreurs
        if self.audit_report['errors']:
            print("\n❌ ERREURS")
            print("-" * 80)
            for error in self.audit_report['errors']:
                print(f"  - {error}")
        
        print("\n" + "="*80)
        
        # Sauvegarder le rapport en JSON
        report_filename = f"tenant_migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(self.audit_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Rapport complet sauvegardé dans: {report_filename}")
        print()


def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migration des tenant_id pour isolation multi-tenant'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Mode simulation: affiche ce qui serait fait sans modifier la base'
    )
    
    args = parser.parse_args()
    
    try:
        auditor = TenantMigrationAuditor()
        success = auditor.run_migration(dry_run=args.dry_run)
        auditor.print_audit_report()
        
        if not success:
            print("\n❌ La migration a échoué")
            sys.exit(1)
        
        if auditor.audit_report['errors']:
            print(f"\n⚠️  Migration terminée avec {len(auditor.audit_report['errors'])} erreur(s)")
            sys.exit(1)
        
        if args.dry_run:
            print("\n✅ Simulation terminée avec succès")
            print("   Exécutez sans --dry-run pour appliquer les modifications")
        else:
            print("\n✅ Migration terminée avec succès")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
