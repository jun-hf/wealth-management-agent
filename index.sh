#!/bin/bash

PROJECT_ID=$(gcloud config get-value project)

echo "=========================================="
echo "Creating Firestore Indexes"
echo "Project: $PROJECT_ID"
echo "=========================================="
echo ""

# 1. Basic vector index (REQUIRED for vector search)
echo "1. Creating basic vector index on 'embedding' field..."
gcloud firestore indexes composite create \
  --collection-group=funds \
  --query-scope=COLLECTION \
  --field-config=field-path=embedding,vector-config='{"dimension":"768","flat":{}}' \
  --project=$PROJECT_ID

echo ""
echo "✓ Basic vector index created"
echo ""

# 2. Risk + Vector
echo "2. Creating risk_level + embedding index..."
gcloud firestore indexes composite create \
  --collection-group=funds \
  --query-scope=COLLECTION \
  --field-config=field-path=risk_level,order=ASCENDING \
  --field-config=field-path=embedding,vector-config='{"dimension":"768","flat":{}}' \
  --project=wise-perception-480414-h1

echo ""
echo "✓ Risk filter index created"
echo ""

# 3. Asset class + Vector
echo "3. Creating asset_class + embedding index..."
gcloud firestore indexes composite create \
  --collection-group=funds \
  --query-scope=COLLECTION \
  --field-config=field-path=asset_class,order=ASCENDING \
  --field-config=field-path=embedding,vector-config='{"dimension":"768","flat":{}}' \
  --project=wise-perception-480414-h1

echo ""
echo "✓ Asset class filter index created"
echo ""

# 4. 5yr return + Vector
echo "4. Creating return_5yr + embedding index..."
gcloud firestore indexes composite create \
  --collection-group=funds \
  --query-scope=COLLECTION \
  --field-config=field-path=return_5yr,order=ASCENDING \
  --field-config=field-path=embedding,vector-config='{"dimension":"768","flat":{}}' \
  --project=wise-perception-480414-h1

echo ""
echo "✓ Performance filter index created"
echo ""

# 5. MER + Vector
echo "5. Creating mer + embedding index..."
gcloud firestore indexes composite create \
  --collection-group=funds \
  --query-scope=COLLECTION \
  --field-config=field-path=mer,order=ASCENDING \
  --field-config=field-path=embedding,vector-config='{"dimension":"768","flat":{}}' \
  --project=wise-perception-480414-h1

echo ""
echo "✓ MER filter index created"
echo ""

echo "=========================================="
echo "INDEX CREATION STARTED"
echo "=========================================="
echo ""
echo "⏳ Indexes are being created (takes 5-10 minutes)"
echo ""
echo "Check status with:"
echo "  gcloud firestore indexes composite list"
echo ""
echo "Wait until all indexes show STATE: READY"
echo "=========================================="