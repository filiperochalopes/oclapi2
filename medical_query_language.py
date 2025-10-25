#!/usr/bin/env python3
"""
Medical Concept Query Language (MCQL)
Uma linguagem de busca intuitiva para conceitos médicos

Sintaxe:
    FIND <tipo> [WHERE condições] [WITH relacionamentos] [EXCLUDE condições]
    
Exemplos:
    FIND concept WHERE name contains "diabetes"
    FIND concept WHERE class = "Diagnosis" AND name contains "hypertension"
    FIND concept WITH maps to "SNOMED"
    FIND concept WHERE name contains "fever" EXCLUDE retired
    FIND concept WHERE class in ["Diagnosis", "Symptom"] EXCLUDE (name contains "test" OR name contains "obsolete")
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class TokenType(Enum):
    FIND = "FIND"
    WHERE = "WHERE"
    WITH = "WITH"
    WITHOUT = "WITHOUT"
    EXCLUDE = "EXCLUDE"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    IN = "IN"
    CONTAINS = "CONTAINS"
    EQUALS = "="
    NOT_EQUALS = "!="
    GREATER = ">"
    LESS = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    STRING = "STRING"
    NUMBER = "NUMBER"
    FIELD = "FIELD"
    LPAREN = "("
    RPAREN = ")"
    LBRACKET = "["
    RBRACKET = "]"
    COMMA = ","
    TO = "TO"
    MAPS = "MAPS"
    RETIRED = "RETIRED"
    ACTIVE = "ACTIVE"
    ANY = "ANY"
    ALL = "ALL"
    AT = "AT"
    LEAST = "LEAST"
    MOST = "MOST"
    EXACTLY = "EXACTLY"
    ONE = "ONE"
    OF = "OF"

@dataclass
class Token:
    type: TokenType
    value: Any
    position: int

class MCQLLexer:
    def __init__(self, query: str):
        self.query = query.strip()
        self.position = 0
        self.tokens = []
        
    def tokenize(self) -> List[Token]:
        while self.position < len(self.query):
            self._skip_whitespace()
            if self.position >= len(self.query):
                break
                
            if self.query[self.position] == '"':
                self._read_string()
            elif self.query[self.position] == '(':
                self.tokens.append(Token(TokenType.LPAREN, '(', self.position))
                self.position += 1
            elif self.query[self.position] == ')':
                self.tokens.append(Token(TokenType.RPAREN, ')', self.position))
                self.position += 1
            elif self.query[self.position] == '[':
                self.tokens.append(Token(TokenType.LBRACKET, '[', self.position))
                self.position += 1
            elif self.query[self.position] == ']':
                self.tokens.append(Token(TokenType.RBRACKET, ']', self.position))
                self.position += 1
            elif self.query[self.position] == ',':
                self.tokens.append(Token(TokenType.COMMA, ',', self.position))
                self.position += 1
            elif self.query[self.position:self.position+2] == '!=':
                self.tokens.append(Token(TokenType.NOT_EQUALS, '!=', self.position))
                self.position += 2
            elif self.query[self.position:self.position+2] == '>=':
                self.tokens.append(Token(TokenType.GREATER_EQUAL, '>=', self.position))
                self.position += 2
            elif self.query[self.position:self.position+2] == '<=':
                self.tokens.append(Token(TokenType.LESS_EQUAL, '<=', self.position))
                self.position += 2
            elif self.query[self.position] == '=':
                self.tokens.append(Token(TokenType.EQUALS, '=', self.position))
                self.position += 1
            elif self.query[self.position] == '>':
                self.tokens.append(Token(TokenType.GREATER, '>', self.position))
                self.position += 1
            elif self.query[self.position] == '<':
                self.tokens.append(Token(TokenType.LESS, '<', self.position))
                self.position += 1
            elif self.query[self.position].isdigit():
                self._read_number()
            else:
                self._read_word()
                
        return self.tokens
    
    def _skip_whitespace(self):
        while self.position < len(self.query) and self.query[self.position].isspace():
            self.position += 1
    
    def _read_string(self):
        start = self.position
        self.position += 1  # Skip opening quote
        value = ""
        while self.position < len(self.query) and self.query[self.position] != '"':
            value += self.query[self.position]
            self.position += 1
        self.position += 1  # Skip closing quote
        self.tokens.append(Token(TokenType.STRING, value, start))
    
    def _read_number(self):
        start = self.position
        value = ""
        while self.position < len(self.query) and (self.query[self.position].isdigit() or self.query[self.position] == '.'):
            value += self.query[self.position]
            self.position += 1
        self.tokens.append(Token(TokenType.NUMBER, float(value) if '.' in value else int(value), start))
    
    def _read_word(self):
        start = self.position
        value = ""
        while self.position < len(self.query) and (self.query[self.position].isalnum() or self.query[self.position] in ['_', '-']):
            value += self.query[self.position]
            self.position += 1
            
        upper_value = value.upper()
        token_type = {
            'FIND': TokenType.FIND,
            'WHERE': TokenType.WHERE,
            'WITH': TokenType.WITH,
            'WITHOUT': TokenType.WITHOUT,
            'EXCLUDE': TokenType.EXCLUDE,
            'AND': TokenType.AND,
            'OR': TokenType.OR,
            'NOT': TokenType.NOT,
            'IN': TokenType.IN,
            'CONTAINS': TokenType.CONTAINS,
            'TO': TokenType.TO,
            'MAPS': TokenType.MAPS,
            'RETIRED': TokenType.RETIRED,
            'ACTIVE': TokenType.ACTIVE,
            'ANY': TokenType.ANY,
            'ALL': TokenType.ALL,
            'AT': TokenType.AT,
            'LEAST': TokenType.LEAST,
            'MOST': TokenType.MOST,
            'EXACTLY': TokenType.EXACTLY,
            'ONE': TokenType.ONE,
            'OF': TokenType.OF,
        }.get(upper_value, TokenType.FIELD)
        
        self.tokens.append(Token(token_type, value if token_type == TokenType.FIELD else upper_value, start))

class MCQLParser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.current_token = tokens[0] if tokens else None
        
    def parse(self) -> Dict[str, Any]:
        query: Dict[str, Any] = {
            'type': None,
            'where': None,
            'with': None,
            'without': None,
            'exclude': None
        }
        
        # FIND clause
        if self.current_token and self.current_token.type == TokenType.FIND:
            self._next()
            if self.current_token and self.current_token.type == TokenType.FIELD:
                query['type'] = self.current_token.value
                self._next()
        
        # WHERE clause
        if self.current_token and self.current_token.type == TokenType.WHERE:
            self._next()
            query['where'] = self._parse_condition()
        
        # WITH clause
        if self.current_token and self.current_token.type == TokenType.WITH:
            self._next()
            query['with'] = self._parse_with()
        
        # WITHOUT clause
        if self.current_token and self.current_token.type == TokenType.WITHOUT:
            self._next()
            query['without'] = self._parse_without()
        
        # EXCLUDE clause
        if self.current_token and self.current_token.type == TokenType.EXCLUDE:
            self._next()
            query['exclude'] = self._parse_condition()
            
        return query
    
    def _next(self):
        self.position += 1
        self.current_token = self.tokens[self.position] if self.position < len(self.tokens) else None
    
    def _parse_condition(self) -> Dict[str, Any]:
        if self.current_token and self.current_token.type == TokenType.LPAREN:
            self._next()
            condition = self._parse_condition()
            if self.current_token and self.current_token.type == TokenType.RPAREN:
                self._next()
            return condition
        
        if self.current_token and self.current_token.type == TokenType.NOT:
            self._next()
            return {'not': self._parse_condition()}
        
        if self.current_token and self.current_token.type == TokenType.RETIRED:
            self._next()
            return {'field': 'retired', 'op': '=', 'value': 1}
        
        if self.current_token and self.current_token.type == TokenType.ACTIVE:
            self._next()
            return {'field': 'retired', 'op': '=', 'value': 0}
        
        # Parse simple condition
        left = self._parse_simple_condition()
        
        # Check for AND/OR
        if self.current_token and self.current_token.type in [TokenType.AND, TokenType.OR]:
            op = self.current_token.type
            self._next()
            right = self._parse_condition()
            return {
                'type': 'and' if op == TokenType.AND else 'or',
                'conditions': [left, right]
            }
        
        return left
    
    def _parse_simple_condition(self) -> Dict[str, Any]:
        field = None
        if self.current_token and self.current_token.type == TokenType.FIELD:
            field = self.current_token.value
            self._next()
        
        op = None
        if self.current_token and self.current_token.type in [TokenType.EQUALS, TokenType.NOT_EQUALS, 
                                                               TokenType.GREATER, TokenType.LESS,
                                                               TokenType.GREATER_EQUAL, TokenType.LESS_EQUAL,
                                                               TokenType.CONTAINS, TokenType.IN]:
            op = self.current_token.value if isinstance(self.current_token.value, str) else self.current_token.type.value
            self._next()
        
        value = None
        if self.current_token:
            if self.current_token.type == TokenType.STRING:
                value = self.current_token.value
                self._next()
            elif self.current_token.type == TokenType.NUMBER:
                value = self.current_token.value
                self._next()
            elif self.current_token.type == TokenType.LBRACKET:
                value = self._parse_list()
        
        return {'field': field, 'op': op, 'value': value}
    
    def _parse_list(self) -> List[Any]:
        values = []
        self._next()  # Skip [
        
        while self.current_token and self.current_token.type != TokenType.RBRACKET:
            if self.current_token.type == TokenType.STRING:
                values.append(self.current_token.value)
            elif self.current_token.type == TokenType.NUMBER:
                values.append(self.current_token.value)
            self._next()
            
            if self.current_token and self.current_token.type == TokenType.COMMA:
                self._next()
        
        if self.current_token and self.current_token.type == TokenType.RBRACKET:
            self._next()
            
        return values
    
    def _parse_with(self) -> Dict[str, Any]:
        condition = {}
        
        if self.current_token and self.current_token.type == TokenType.MAPS:
            self._next()
            if self.current_token and self.current_token.type == TokenType.TO:
                self._next()
            
            # Check for quantifiers (e.g., EXACTLY 2 OF, AT LEAST 1 OF)
            quantifier = self._parse_quantifier()
            
            # Parse the value(s)
            if self.current_token:
                if self.current_token.type == TokenType.STRING:
                    condition = {'maps_to': self.current_token.value}
                    if quantifier:
                        condition['quantifier'] = quantifier
                    self._next()
                elif self.current_token.type == TokenType.LBRACKET:
                    values = self._parse_list()
                    condition = {'maps_to': values}
                    if quantifier:
                        condition['quantifier'] = quantifier
        
        return condition
    
    def _parse_without(self) -> Dict[str, Any]:
        condition = {}
        
        if self.current_token and self.current_token.type == TokenType.MAPS:
            self._next()
            if self.current_token and self.current_token.type == TokenType.TO:
                self._next()
            
            # Check for quantifiers (ANY, ALL, AT LEAST ONE OF, etc.)
            quantifier = self._parse_quantifier()
            
            # Parse the value(s)
            if self.current_token:
                if self.current_token.type == TokenType.STRING:
                    condition = {
                        'maps_to': self.current_token.value,
                        'quantifier': quantifier if quantifier else 'any'
                    }
                    self._next()
                elif self.current_token.type == TokenType.LBRACKET:
                    values = self._parse_list()
                    condition = {
                        'maps_to': values,
                        'quantifier': quantifier if quantifier else 'any'
                    }
        
        return condition
    
    def _parse_quantifier(self) -> Optional[Dict[str, Any]]:
        """Parse quantifiers like ANY, ALL, AT LEAST 2 OF, etc."""
        if not self.current_token:
            return None
        
        # Simple quantifiers
        if self.current_token.type == TokenType.ANY:
            self._next()
            return {'type': 'any'}
        elif self.current_token.type == TokenType.ALL:
            self._next()
            return {'type': 'all'}
        
        # Complex quantifiers (AT LEAST/MOST/EXACTLY N OF)
        elif self.current_token.type == TokenType.AT:
            self._next()
            if self.current_token and self.current_token.type == TokenType.LEAST:
                self._next()
                if self.current_token and self.current_token.type == TokenType.NUMBER:
                    count = self.current_token.value
                    self._next()
                    if self.current_token and self.current_token.type == TokenType.OF:
                        self._next()
                    return {'type': 'at_least', 'count': count}
                elif self.current_token and self.current_token.type == TokenType.ONE:
                    self._next()
                    if self.current_token and self.current_token.type == TokenType.OF:
                        self._next()
                    return {'type': 'at_least', 'count': 1}
            elif self.current_token and self.current_token.type == TokenType.MOST:
                self._next()
                if self.current_token and self.current_token.type == TokenType.NUMBER:
                    count = self.current_token.value
                    self._next()
                    if self.current_token and self.current_token.type == TokenType.OF:
                        self._next()
                    return {'type': 'at_most', 'count': count}
                elif self.current_token and self.current_token.type == TokenType.ONE:
                    self._next()
                    if self.current_token and self.current_token.type == TokenType.OF:
                        self._next()
                    return {'type': 'at_most', 'count': 1}
        
        elif self.current_token.type == TokenType.EXACTLY:
            self._next()
            if self.current_token and self.current_token.type == TokenType.NUMBER:
                count = self.current_token.value
                self._next()
                if self.current_token and self.current_token.type == TokenType.OF:
                    self._next()
                return {'type': 'exactly', 'count': count}
            elif self.current_token and self.current_token.type == TokenType.ONE:
                self._next()
                if self.current_token and self.current_token.type == TokenType.OF:
                    self._next()
                return {'type': 'exactly', 'count': 1}
        
        return None

class MCQLToSQL:
    def __init__(self):
        self.field_mappings = {
            'name': 'cn.name',
            'class': 'cc.name',
            'description': 'c.description',
            'uuid': 'c.uuid',
            'id': 'c.concept_id',
            'retired': 'c.retired',
            'created': 'c.date_created',
            'source': 'crs.name',
            'term': 'crt.name',
            'code': 'crt.code'
        }
    
    def convert(self, parsed_query: Dict[str, Any]) -> str:
        tables = ['concept c']
        joins = []
        where_conditions = ['c.retired = 0']  # Default: only active concepts
        
        # Analyze needed joins
        needs_name = self._needs_field(parsed_query, ['name'])
        needs_class = self._needs_field(parsed_query, ['class'])
        needs_map = (parsed_query.get('with') and 'maps_to' in parsed_query['with']) or \
                    (parsed_query.get('without') and 'maps_to' in parsed_query.get('without', {}))
        
        if needs_name:
            joins.append('LEFT JOIN concept_name cn ON c.concept_id = cn.concept_id')
        if needs_class:
            joins.append('LEFT JOIN concept_class cc ON c.class_id = cc.concept_class_id')
        if needs_map and not parsed_query.get('without'):
            joins.append('LEFT JOIN concept_reference_map crm ON c.concept_id = crm.concept_id')
            joins.append('LEFT JOIN concept_reference_term crt ON crm.concept_reference_term_id = crt.concept_reference_term_id')
            joins.append('LEFT JOIN concept_reference_source crs ON crt.concept_source_id = crs.concept_source_id')
        
        # Process WHERE conditions
        if parsed_query.get('where'):
            where_sql = self._condition_to_sql(parsed_query['where'])
            if where_sql:
                where_conditions.append(f"({where_sql})")
        
        # Process WITH conditions
        if parsed_query.get('with') and 'maps_to' in parsed_query['with']:
            with_data = parsed_query['with']
            quantifier = with_data.get('quantifier', {})
            
            if isinstance(with_data['maps_to'], str):
                where_conditions.append(f"crs.name LIKE '%{with_data['maps_to']}%'")
            elif isinstance(with_data['maps_to'], list):
                sources = with_data['maps_to']
                sources_str = "', '".join(sources)
                
                if quantifier.get('type') == 'exactly':
                    count = quantifier.get('count', len(sources))
                    subquery = f"""c.concept_id IN (
                        SELECT concept_id FROM (
                            SELECT crm.concept_id, COUNT(DISTINCT crs.name) as source_count
                            FROM concept_reference_map crm
                            JOIN concept_reference_term crt ON crm.concept_reference_term_id = crt.concept_reference_term_id
                            JOIN concept_reference_source crs ON crt.concept_source_id = crs.concept_source_id
                            WHERE crs.name IN ('{sources_str}')
                            GROUP BY crm.concept_id
                            HAVING source_count = {count}
                        ) AS exact_matches
                    )"""
                    where_conditions.append(subquery)
                elif quantifier.get('type') == 'at_least':
                    count = quantifier.get('count', 1)
                    subquery = f"""c.concept_id IN (
                        SELECT concept_id FROM (
                            SELECT crm.concept_id, COUNT(DISTINCT crs.name) as source_count
                            FROM concept_reference_map crm
                            JOIN concept_reference_term crt ON crm.concept_reference_term_id = crt.concept_reference_term_id
                            JOIN concept_reference_source crs ON crt.concept_source_id = crs.concept_source_id
                            WHERE crs.name IN ('{sources_str}')
                            GROUP BY crm.concept_id
                            HAVING source_count >= {count}
                        ) AS min_matches
                    )"""
                    where_conditions.append(subquery)
                elif quantifier.get('type') == 'at_most':
                    count = quantifier.get('count', len(sources))
                    subquery = f"""c.concept_id IN (
                        SELECT concept_id FROM (
                            SELECT crm.concept_id, COUNT(DISTINCT crs.name) as source_count
                            FROM concept_reference_map crm
                            JOIN concept_reference_term crt ON crm.concept_reference_term_id = crt.concept_reference_term_id
                            JOIN concept_reference_source crs ON crt.concept_source_id = crs.concept_source_id
                            WHERE crs.name IN ('{sources_str}')
                            GROUP BY crm.concept_id
                            HAVING source_count <= {count}
                        ) AS max_matches
                    )"""
                    where_conditions.append(subquery)
                else:  # Default or 'all'
                    where_conditions.append(f"crs.name IN ('{sources_str}')")
        
        # Process WITHOUT conditions
        if parsed_query.get('without') and 'maps_to' in parsed_query['without']:
            without_data = parsed_query['without']
            quantifier = without_data.get('quantifier', {'type': 'any'})
            
            if isinstance(without_data['maps_to'], str):
                # Single source - just exclude it
                subquery = f"""c.concept_id NOT IN (
                    SELECT DISTINCT crm.concept_id
                    FROM concept_reference_map crm
                    JOIN concept_reference_term crt ON crm.concept_reference_term_id = crt.concept_reference_term_id
                    JOIN concept_reference_source crs ON crt.concept_source_id = crs.concept_source_id
                    WHERE crs.name LIKE '%{without_data['maps_to']}%'
                )"""
                where_conditions.append(subquery)
            elif isinstance(without_data['maps_to'], list):
                sources = without_data['maps_to']
                sources_str = "', '".join(sources)
                
                if quantifier.get('type') == 'any':
                    # WITHOUT ANY - doesn't have any of the sources
                    subquery = f"""c.concept_id NOT IN (
                        SELECT DISTINCT crm.concept_id
                        FROM concept_reference_map crm
                        JOIN concept_reference_term crt ON crm.concept_reference_term_id = crt.concept_reference_term_id
                        JOIN concept_reference_source crs ON crt.concept_source_id = crs.concept_source_id
                        WHERE crs.name IN ('{sources_str}')
                    )"""
                    where_conditions.append(subquery)
                elif quantifier.get('type') == 'all':
                    # WITHOUT ALL - doesn't have all of them together
                    subquery = f"""c.concept_id NOT IN (
                        SELECT concept_id FROM (
                            SELECT crm.concept_id, COUNT(DISTINCT crs.name) as source_count
                            FROM concept_reference_map crm
                            JOIN concept_reference_term crt ON crm.concept_reference_term_id = crt.concept_reference_term_id
                            JOIN concept_reference_source crs ON crt.concept_source_id = crs.concept_source_id
                            WHERE crs.name IN ('{sources_str}')
                            GROUP BY crm.concept_id
                            HAVING source_count = {len(sources)}
                        ) AS complete_mappings
                    )"""
                    where_conditions.append(subquery)
                elif quantifier.get('type') == 'at_least' and quantifier.get('count') == 1:
                    # WITHOUT AT LEAST ONE OF - same as WITHOUT ALL
                    subquery = f"""c.concept_id NOT IN (
                        SELECT concept_id FROM (
                            SELECT crm.concept_id, COUNT(DISTINCT crs.name) as source_count
                            FROM concept_reference_map crm
                            JOIN concept_reference_term crt ON crm.concept_reference_term_id = crt.concept_reference_term_id
                            JOIN concept_reference_source crs ON crt.concept_source_id = crs.concept_source_id
                            WHERE crs.name IN ('{sources_str}')
                            GROUP BY crm.concept_id
                            HAVING source_count = {len(sources)}
                        ) AS complete_mappings
                    )"""
                    where_conditions.append(subquery)
        
        # Process EXCLUDE conditions
        if parsed_query.get('exclude'):
            exclude_sql = self._condition_to_sql(parsed_query['exclude'])
            if exclude_sql:
                where_conditions.append(f"NOT ({exclude_sql})")
        
        # Build SQL
        sql = "SELECT DISTINCT c.concept_id, c.uuid, c.description"
        if needs_name:
            sql += ", cn.name as concept_name"
        if needs_class:
            sql += ", cc.name as class_name"
        
        sql += f"\nFROM {tables[0]}"
        for join in joins:
            sql += f"\n{join}"
        
        if where_conditions:
            sql += f"\nWHERE {' AND '.join(where_conditions)}"
        
        sql += "\nLIMIT 100"
        
        return sql
    
    def _needs_field(self, query: Dict[str, Any], fields: List[str]) -> bool:
        def check_condition(cond):
            if not cond:
                return False
            if isinstance(cond, dict):
                if 'field' in cond and cond['field'] in fields:
                    return True
                if 'not' in cond:
                    return check_condition(cond['not'])
                if 'conditions' in cond:
                    return any(check_condition(c) for c in cond['conditions'])
            return False
        
        return check_condition(query.get('where')) or check_condition(query.get('exclude'))
    
    def _condition_to_sql(self, condition: Dict[str, Any]) -> str:
        if not condition:
            return ""
        
        if 'not' in condition:
            inner = self._condition_to_sql(condition['not'])
            return f"NOT ({inner})" if inner else ""
        
        if 'type' in condition:
            if condition['type'] == 'and':
                parts = [self._condition_to_sql(c) for c in condition['conditions']]
                parts = [p for p in parts if p]
                return f"({' AND '.join(parts)})" if parts else ""
            elif condition['type'] == 'or':
                parts = [self._condition_to_sql(c) for c in condition['conditions']]
                parts = [p for p in parts if p]
                return f"({' OR '.join(parts)})" if parts else ""
        
        if 'field' in condition and 'op' in condition:
            field = self.field_mappings.get(condition['field'], condition['field'])
            op = condition['op']
            value = condition['value']
            
            if op == 'CONTAINS':
                return f"{field} LIKE '%{value}%'"
            elif op == 'IN':
                if isinstance(value, list):
                    values = "', '".join(str(v) for v in value)
                    return f"{field} IN ('{values}')"
            elif op == '=':
                if isinstance(value, str):
                    return f"{field} = '{value}'"
                else:
                    return f"{field} = {value}"
            elif op == '!=':
                if isinstance(value, str):
                    return f"{field} != '{value}'"
                else:
                    return f"{field} != {value}"
            elif op in ['>', '<', '>=', '<=']:
                return f"{field} {op} {value}"
        
        return ""

class MedicalQueryEngine:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.connection_params = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database
        }
    
    def query(self, mcql_query: str) -> Tuple[str, List[Dict]]:
        # Parse MCQL
        lexer = MCQLLexer(mcql_query)
        tokens = lexer.tokenize()
        
        parser = MCQLParser(tokens)
        parsed = parser.parse()
        
        # Convert to SQL
        converter = MCQLToSQL()
        sql = converter.convert(parsed)
        
        # For now, return the SQL query
        # In production, you would execute this against the database
        return sql, []
    
    def explain(self, mcql_query: str) -> Dict[str, Any]:
        """Explain what the query will do"""
        lexer = MCQLLexer(mcql_query)
        tokens = lexer.tokenize()
        
        parser = MCQLParser(tokens)
        parsed = parser.parse()
        
        explanation = {
            'parsed_query': parsed,
            'description': self._generate_description(parsed),
            'sql': MCQLToSQL().convert(parsed)
        }
        
        return explanation
    
    def _generate_description(self, parsed: Dict[str, Any]) -> str:
        desc = "Search for concepts"
        
        if parsed.get('where'):
            desc += " where " + self._describe_condition(parsed['where'])
        
        if parsed.get('with'):
            if 'maps_to' in parsed['with']:
                with_data = parsed['with']
                quantifier = with_data.get('quantifier', {})
                maps_to = with_data['maps_to']
                
                if quantifier.get('type') == 'exactly':
                    desc += f" that map to exactly {quantifier.get('count')} of {maps_to}"
                elif quantifier.get('type') == 'at_least':
                    desc += f" that map to at least {quantifier.get('count')} of {maps_to}"
                elif quantifier.get('type') == 'at_most':
                    desc += f" that map to at most {quantifier.get('count')} of {maps_to}"
                else:
                    desc += f" that map to {maps_to}"
        
        if parsed.get('without'):
            if 'maps_to' in parsed['without']:
                without_data = parsed['without']
                quantifier = without_data.get('quantifier', {'type': 'any'})
                maps_to = without_data['maps_to']
                
                if isinstance(maps_to, str):
                    desc += f" without mapping to {maps_to}"
                elif isinstance(quantifier, dict):
                    if quantifier.get('type') == 'any':
                        desc += f" without mapping to any of {maps_to}"
                    elif quantifier.get('type') == 'all':
                        desc += f" without mapping to all of {maps_to}"
                    elif quantifier.get('type') == 'at_least' and quantifier.get('count') == 1:
                        desc += f" without at least one of {maps_to}"
                else:
                    desc += f" without mapping to {maps_to}"
        
        if parsed.get('exclude'):
            desc += " excluding " + self._describe_condition(parsed['exclude'])
        
        desc += " (only active concepts by default)"
        
        return desc
    
    def _describe_condition(self, cond: Dict[str, Any]) -> str:
        if 'not' in cond:
            return "not " + self._describe_condition(cond['not'])
        
        if 'type' in cond:
            if cond['type'] == 'and':
                parts = [self._describe_condition(c) for c in cond['conditions']]
                return " and ".join(parts)
            elif cond['type'] == 'or':
                parts = [self._describe_condition(c) for c in cond['conditions']]
                return " or ".join(parts)
        
        if 'field' in cond:
            field = cond['field']
            op = cond['op']
            value = cond['value']
            
            if op == 'CONTAINS':
                return f"{field} contains '{value}'"
            elif op == 'IN':
                return f"{field} is one of {value}"
            elif op == '=':
                if field == 'retired' and value == 1:
                    return "retired concepts"
                elif field == 'retired' and value == 0:
                    return "active concepts"
                return f"{field} equals {value}"
            else:
                return f"{field} {op} {value}"
        
        return ""

# Exemplos de uso
if __name__ == "__main__":
    print("Medical Concept Query Language (MCQL)")
    print("=" * 50)
    
    # Exemplos de queries
    examples = [
        'FIND concept WHERE name contains "diabetes"',
        'FIND concept WHERE class = "Diagnosis" AND name contains "hypertension"',
        'FIND concept WHERE name contains "fever" EXCLUDE retired',
        'FIND concept WITH maps to "SNOMED"',
        'FIND concept WHERE class in ["Diagnosis", "Symptom"] EXCLUDE (name contains "test" OR name contains "obsolete")',
        'FIND concept WHERE name contains "COVID" AND class = "Diagnosis" WITH maps to "ICD10"',
        # New WITHOUT examples
        'FIND concept WHERE class = "Drug" WITHOUT maps to ANY ["SNOMED CT", "RxNORM", "WHOATC"]',
        'FIND concept WHERE class = "Drug" WITHOUT maps to ALL ["SNOMED CT", "RxNORM", "WHOATC"]',
        'FIND concept WHERE class = "Drug" WITHOUT maps to AT LEAST ONE OF ["SNOMED CT", "RxNORM", "WHOATC"]',
        'FIND concept WHERE class = "Diagnosis" WITH maps to EXACTLY 2 OF ["SNOMED", "ICD10", "LOINC"]',
        'FIND concept WHERE class = "Test" WITH maps to AT LEAST 1 OF ["LOINC", "CPT"]'
    ]
    
    engine = MedicalQueryEngine(
        host="db.filipelopes.me",
        port=33066,
        user="openmrs",
        password="strongpass",
        database="snapshot_20250920"
    )
    
    for example in examples:
        print(f"\nQuery: {example}")
        explanation = engine.explain(example)
        print(f"Description: {explanation['description']}")
        print(f"SQL:\n{explanation['sql']}")
        print("-" * 50)