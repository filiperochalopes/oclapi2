# MODEL_DATA - Estrutura de Tabelas e Relacionamentos do OCLAPI2

## Visão Geral
OCLAPI2 é um serviço de terminologia médica que gerencia conceitos, mapeamentos, fontes (sources) e coleções. O sistema usa Django com PostgreSQL e Elasticsearch.

## Modelos Base

### BaseModel (abstrato)
- **Campos comuns**: id, public_access, created_at, updated_at, created_by, updated_by, is_active, extras, uri
- **Relacionamentos**: created_by/updated_by → UserProfile
- Todos os modelos herdam desta classe base

### VersionedModel (abstrato)
- Herda de BaseModel
- **Campos adicionais**: version, released, retired, is_latest_version, versioned_object_id
- Usado para recursos que suportam versionamento (Concept, Mapping, Source, Collection)

### ConceptContainerModel (abstrato)
- Herda de VersionedModel
- Base para Sources e Collections
- **Campos**: name, full_name, description, custom_validation_schema, website, external_id
- **Relacionamentos**: organization (ForeignKey) OU user (ForeignKey)

## Modelos Principais

### 1. UserProfile (user_profiles)
- Herda de AbstractUser + BaseModel
- **Campos principais**: username, email, first_name, last_name, verified, verification_token, company, location
- **Relacionamentos**:
  - organizations → ManyToMany(Organization) via members
  - api_rate_limit → OneToOne(UserRateLimit)
  - followers/following → GenericRelation(Follow)
  - Criador de: Sources, Collections, Concepts, Mappings

### 2. Organization (organizations)
- **Campos**: mnemonic (unique), name, company, website, location, description
- **Relacionamentos**:
  - members → ManyToMany(UserProfile)
  - source_set → OneToMany(Source)
  - collection_set → OneToMany(Collection)
  - client_configs → GenericRelation(ClientConfig)

### 3. Source (sources)
- Container para Concepts e Mappings
- **Campos principais**: 
  - mnemonic, version, source_type, hierarchy_meaning
  - autoid_* (configurações para IDs automáticos)
  - properties, filters (ArrayFields)
- **Relacionamentos**:
  - parent → Organization OU UserProfile
  - concepts_set → OneToMany(Concept)
  - mappings_set → OneToMany(Mapping)
  - hierarchy_root → ForeignKey(Concept)
- **Constraints únicos**: (mnemonic, version, organization) OU (mnemonic, version, user)

### 4. Concept (concepts)
- **Campos**: mnemonic, version, concept_class, datatype, retired, external_id
- **Relacionamentos**:
  - parent → ForeignKey(Source)
  - versioned_object → ForeignKey(self) - para versionamento
  - names → OneToMany(ConceptName)
  - descriptions → OneToMany(ConceptDescription)
  - parent_concepts → ManyToMany(self) via ConceptParentRelationship
  - mappings_from/mappings_to → OneToMany(Mapping)

### 5. ConceptName (concept_names)
- **Campos**: name, type, locale, locale_preferred, external_id
- **Relacionamento**: concept → ForeignKey(Concept)

### 6. ConceptDescription (concept_descriptions)
- **Campos**: name (description text), type, locale, locale_preferred, external_id
- **Relacionamento**: concept → ForeignKey(Concept)

### 7. Mapping (mappings)
- **Campos principais**: 
  - mnemonic, map_type, external_id, sort_weight
  - from_concept_code, to_concept_code (novo schema)
  - from_source_url, to_source_url
- **Relacionamentos**:
  - parent → ForeignKey(Source)
  - from_concept → ForeignKey(Concept)
  - to_concept → ForeignKey(Concept)
  - from_source/to_source → ForeignKey(Source)
  - sources → ManyToMany(Source)
- **Constraint único**: (mnemonic, version, parent)

### 8. Collection (collections)
- Container que referencia Concepts e Mappings
- **Campos**: mnemonic, version, collection_type, autoexpand, immutable
- **Relacionamentos**:
  - parent → Organization OU UserProfile
  - references → OneToMany(CollectionReference)
  - concepts → ManyToMany(Concept) via expansions
  - mappings → ManyToMany(Mapping) via expansions

### 9. CollectionReference (collection_references)
- **Campos**: expression (URI do recurso), reference_type
- **Relacionamentos**:
  - collection → ForeignKey(Collection)
  - concepts/mappings → ManyToMany via expansions

### 10. Task (tasks)
- Sistema de tarefas assíncronas
- **Campos**: queue, name, state, details, result, retry_count
- **Relacionamentos**: created_by, updated_by → UserProfile

## Modelos Auxiliares

### Bundle (bundles)
- Representa recursos FHIR Bundle
- **Relacionamentos**: root_resource (GenericForeignKey)

### ClientConfig (client_configs)
- Configurações específicas do cliente
- **Campos**: type, name, config (JSONField)
- **Relacionamento**: resource (GenericForeignKey) → Organization/Source/Collection

### Event (events)  
- Log de eventos do sistema
- **Campos**: event_type, object_url, referenced_object_url
- **Relacionamentos**: actor → UserProfile

### Pin (pins)
- Recursos fixados pelos usuários
- **Relacionamentos**: 
  - user → ForeignKey(UserProfile)
  - resource (GenericForeignKey)

### Toggle (toggles)
- Feature flags do sistema
- **Campos**: name, enabled, restrictions

### URLRegistry (url_registries)
- Registro de URLs canônicas
- **Campos**: url, namespace, name
- **Relacionamentos**: organization → ForeignKey

## Índices Importantes

### Sources
- (mnemonic, version, organization) - único
- (mnemonic, version, user) - único
- source_org_released, source_user_released

### Concepts
- (mnemonic, parent_id, version) - único
- concept_latest_source_mnemonic
- concept_parent, concept_latest

### Mappings
- (mnemonic, version, parent) - único
- direct_mappings, repo_version_mappings
- mappings_sort_weight_next

### Collections
- (mnemonic, version, organization) - único
- (mnemonic, version, user) - único
- coll_org_released, coll_user_released

## Fluxo de Dados

1. **Hierarquia de Propriedade**:
   - UserProfile/Organization → Sources/Collections
   - Sources → Concepts/Mappings
   - Collections → References → Concepts/Mappings (via expansões)

2. **Versionamento**:
   - Source/Collection HEAD aponta para última versão
   - Concepts/Mappings herdam versões do Source pai
   - versioned_object_id conecta versões do mesmo recurso

3. **Expansões de Coleções**:
   - CollectionReference define o que incluir
   - Processo de expansão materializa references em concepts/mappings
   - Autoexpand atualiza automaticamente com mudanças

4. **Elasticsearch**:
   - Documentos espelhados para busca rápida
   - Sincronização via sinais Django
   - Índices separados por tipo de recurso

## Validações e Constraints

- **Mnemonics**: Devem seguir NAMESPACE_REGEX
- **Versions**: "HEAD" é reservado para última versão
- **Locales**: ConceptNames com locale_preferred único por idioma
- **Hierarchy**: hierarchy_root deve pertencer ao mesmo Source
- **References**: Validação de URIs e existência de recursos