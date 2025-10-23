#!/bin/bash
# Calculate ECR Pull-Through Cache Costs
# This script helps estimate monthly costs for pull-through cache implementation

set -e

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   ECR Pull-Through Cache Cost Calculator${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""

# Get user inputs
read -p "How many builds per day? (default: 3): " BUILDS_PER_DAY
BUILDS_PER_DAY=${BUILDS_PER_DAY:-3}

read -p "Average build duration in minutes? (default: 8): " BUILD_MINUTES
BUILD_MINUTES=${BUILD_MINUTES:-8}

read -p "Seconds saved per build with cache? (default: 45): " SECONDS_SAVED
SECONDS_SAVED=${SECONDS_SAVED:-45}

read -p "Are you within AWS Free Tier? (y/n, default: y): " IN_FREE_TIER
IN_FREE_TIER=${IN_FREE_TIER:-y}

echo ""
echo -e "${YELLOW}Calculating costs...${NC}"
echo ""

# Constants
CODEBUILD_RATE=0.005  # $ per minute for BUILD_GENERAL1_MEDIUM
ECR_STORAGE_RATE=0.10 # $ per GB per month
BASE_IMAGE_SIZE_MB=80
CACHED_IMAGES=5
TOTAL_CACHE_SIZE_MB=$((BASE_IMAGE_SIZE_MB * CACHED_IMAGES))
TOTAL_CACHE_SIZE_GB=$(echo "scale=3; $TOTAL_CACHE_SIZE_MB / 1024" | bc)

# Calculate monthly builds
MONTHLY_BUILDS=$((BUILDS_PER_DAY * 30))

# Calculate costs WITHOUT cache
BUILD_COST_WITHOUT=$(echo "scale=2; $MONTHLY_BUILDS * $BUILD_MINUTES * $CODEBUILD_RATE" | bc)

# Calculate costs WITH cache
MINUTES_SAVED=$(echo "scale=2; $SECONDS_SAVED / 60" | bc)
BUILD_MINUTES_WITH_CACHE=$(echo "scale=2; $BUILD_MINUTES - $MINUTES_SAVED" | bc)
BUILD_COST_WITH=$(echo "scale=2; $MONTHLY_BUILDS * $BUILD_MINUTES_WITH_CACHE * $CODEBUILD_RATE" | bc)

# ECR storage cost
if [ "$IN_FREE_TIER" = "y" ] || [ "$IN_FREE_TIER" = "Y" ]; then
    if (( $(echo "$TOTAL_CACHE_SIZE_MB < 500" | bc -l) )); then
        ECR_STORAGE_COST=0.00
        FREE_TIER_NOTE="(within 500 MB free tier)"
    else
        BILLABLE_GB=$(echo "scale=3; ($TOTAL_CACHE_SIZE_MB - 500) / 1024" | bc)
        ECR_STORAGE_COST=$(echo "scale=2; $BILLABLE_GB * $ECR_STORAGE_RATE" | bc)
        FREE_TIER_NOTE="(first 500 MB free)"
    fi
else
    ECR_STORAGE_COST=$(echo "scale=2; $TOTAL_CACHE_SIZE_GB * $ECR_STORAGE_RATE" | bc)
    FREE_TIER_NOTE=""
fi

# Total costs
TOTAL_WITHOUT=$BUILD_COST_WITHOUT
TOTAL_WITH=$(echo "scale=2; $BUILD_COST_WITH + $ECR_STORAGE_COST" | bc)
MONTHLY_SAVINGS=$(echo "scale=2; $TOTAL_WITHOUT - $TOTAL_WITH" | bc)
YEARLY_SAVINGS=$(echo "scale=2; $MONTHLY_SAVINGS * 12" | bc)

# Display results
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   COST BREAKDOWN${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Build Frequency:${NC}"
echo "  • Builds per day: $BUILDS_PER_DAY"
echo "  • Monthly builds: $MONTHLY_BUILDS"
echo ""
echo -e "${YELLOW}WITHOUT Pull-Through Cache:${NC}"
echo "  • Build time: $BUILD_MINUTES minutes/build"
echo "  • Build cost: \$$BUILD_COST_WITHOUT/month"
echo "  • Storage cost: \$0.00/month"
echo -e "  ${RED}• Total: \$$TOTAL_WITHOUT/month${NC}"
echo ""
echo -e "${YELLOW}WITH Pull-Through Cache:${NC}"
echo "  • Build time: $BUILD_MINUTES_WITH_CACHE minutes/build (saved $MINUTES_SAVED min)"
echo "  • Build cost: \$$BUILD_COST_WITH/month"
echo "  • Storage cost: \$$ECR_STORAGE_COST/month $FREE_TIER_NOTE"
echo "  • Cache size: $TOTAL_CACHE_SIZE_MB MB ($CACHED_IMAGES images)"
echo -e "  ${GREEN}• Total: \$$TOTAL_WITH/month${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   SAVINGS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}• Monthly savings: \$$MONTHLY_SAVINGS${NC}"
echo -e "  ${GREEN}• Yearly savings: \$$YEARLY_SAVINGS${NC}"
echo ""

# Recommendations
if (( $(echo "$MONTHLY_SAVINGS > 0" | bc -l) )); then
    echo -e "${GREEN}✅ RECOMMENDATION: Implement pull-through cache${NC}"
    echo -e "   You'll save money and improve build reliability!"
else
    echo -e "${YELLOW}⚠️  RECOMMENDATION: Consider other optimizations${NC}"
    echo -e "   At your current build frequency, savings are minimal."
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""
echo "Additional Benefits (not calculated above):"
echo "  • Eliminated Docker Hub rate limit risks"
echo "  • 3-4x faster image pulls (better developer experience)"
echo "  • Improved build reliability and consistency"
echo "  • ECR vulnerability scanning for cached images"
echo ""
