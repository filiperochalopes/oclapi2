#!/usr/bin/env python3
"""
Test script for Medical Concept Query Language
"""

import pymysql
import json
import os
from dotenv import load_dotenv
from medical_query_language import MedicalQueryEngine, MCQLLexer, MCQLParser, MCQLToSQL

load_dotenv()

def execute_sql(sql, connection_params):
    """Execute SQL and return results"""
    try:
        connection = pymysql.connect(
            host=connection_params['host'],
            port=connection_params['port'],
            user=connection_params['user'],
            password=connection_params['password'],
            database=connection_params['database'],
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            cursor.execute(sql)
            results = cursor.fetchall()
            return results
    except Exception as e:
        print(f"Error executing SQL: {e}")
        return []
    finally:
        if 'connection' in locals():
            connection.close()

def test_mcql_queries():
    """Test MCQL queries against the real database"""

    connection_params = {
        'host': os.getenv('DB_HOST'),
        'port': int(os.getenv('DB_PORT', '33066')),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'database': os.getenv('DB_DATABASE')
    }
    
    engine = MedicalQueryEngine(**connection_params)
    
    # Test queries
    test_cases = [
        {
            'query': 'FIND concept WHERE name contains "diabetes"',
            'description': 'Find all concepts with "diabetes" in the name'
        },
        {
            'query': 'FIND concept WHERE class = "Diagnosis"',
            'description': 'Find all diagnosis concepts'
        },
        {
            'query': 'FIND concept WHERE name contains "fever" EXCLUDE retired',
            'description': 'Find active concepts with "fever" in the name'
        },
        {
            'query': 'FIND concept WITH maps to "SNOMED"',
            'description': 'Find concepts mapped to SNOMED'
        },
        {
            'query': 'FIND concept WHERE class in ["Diagnosis", "Test"] EXCLUDE name contains "obsolete"',
            'description': 'Find diagnosis or test concepts, excluding obsolete ones'
        }
    ]
    
    print("Testing Medical Concept Query Language")
    print("=" * 80)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"MCQL Query: {test['query']}")
        
        # Parse and convert to SQL
        explanation = engine.explain(test['query'])
        sql = explanation['sql']
        
        print(f"Generated SQL:\n{sql}")
        
        # Execute SQL
        results = execute_sql(sql, connection_params)
        
        if results:
            print(f"\nResults found: {len(results)}")
            # Show first 3 results
            for j, result in enumerate(results[:3], 1):
                print(f"  {j}. ID: {result.get('concept_id')}, Name: {result.get('concept_name', 'N/A')}")
        else:
            print("No results found")
        
        print("-" * 80)

def interactive_mode():
    """Interactive MCQL shell"""
    connection_params = {
        'host': os.getenv('DB_HOST'),
        'port': int(os.getenv('DB_PORT', '33066')),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'database': os.getenv('DB_DATABASE')
    }
    
    engine = MedicalQueryEngine(**connection_params)
    
    print("\nMedical Concept Query Language - Interactive Mode")
    print("Type 'help' for examples, 'quit' to exit")
    print("=" * 80)
    
    while True:
        try:
            query = input("\nMCQL> ").strip()
            
            if query.lower() == 'quit':
                break
            
            if query.lower() == 'help':
                print("\nExample queries:")
                print('  FIND concept WHERE name contains "diabetes"')
                print('  FIND concept WHERE class = "Diagnosis"')
                print('  FIND concept WITH maps to "SNOMED"')
                print('  FIND concept WHERE name contains "test" EXCLUDE retired')
                print('  FIND concept WHERE class in ["Diagnosis", "Symptom"]')
                print('\n  # New WITHOUT clause examples:')
                print('  FIND concept WHERE class = "Drug" WITHOUT maps to ANY ["SNOMED CT", "RxNORM"]')
                print('  FIND concept WHERE class = "Drug" WITHOUT maps to ALL ["SNOMED CT", "RxNORM"]')
                print('  FIND concept WITH maps to EXACTLY 2 OF ["SNOMED", "ICD10", "LOINC"]')
                print('  FIND concept WITH maps to AT LEAST 1 OF ["LOINC", "CPT"]')
                continue
            
            if not query:
                continue
            
            # Parse and convert
            try:
                explanation = engine.explain(query)
                sql = explanation['sql']
                
                print(f"\nGenerated SQL:\n{sql}")
                
                # Execute
                results = execute_sql(sql, connection_params)
                
                if results:
                    print(f"\nFound {len(results)} results:")
                    for i, result in enumerate(results[:10], 1):
                        name = result.get('concept_name', result.get('description', 'N/A'))
                        
                        # Get FULLY_SPECIFIED name for this concept
                        fully_specified_sql = f"""
                        SELECT name 
                        FROM concept_name 
                        WHERE concept_id = {result.get('concept_id')} 
                        AND concept_name_type = 'FULLY_SPECIFIED'
                        AND locale = 'en'
                        AND voided = 0
                        LIMIT 1
                        """
                        
                        fully_specified_results = execute_sql(fully_specified_sql, connection_params)
                        fully_specified_name = fully_specified_results[0]['name'] if fully_specified_results else name
                        
                        print(f"  {i}. [{result.get('concept_id')}] {fully_specified_name}")
                    
                    if len(results) > 10:
                        print(f"  ... and {len(results) - 10} more")
                else:
                    print("No results found")
                    
            except Exception as e:
                print(f"Error: {e}")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        interactive_mode()
    else:
        test_mcql_queries()