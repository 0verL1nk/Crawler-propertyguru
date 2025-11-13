// API Base URL
const API_BASE = '/api/v1';

// Search function
async function search() {
    const query = document.getElementById('searchInput').value.trim();
    
    if (!query) {
        alert('Please enter your search query');
        return;
    }

    // Show loading
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('results').innerHTML = '';
    document.getElementById('noResults').classList.add('hidden');
    document.getElementById('searchStats').classList.add('hidden');
    document.getElementById('intentDisplay').classList.add('hidden');

    // Build request
    const request = {
        query: query,
        filters: {},
        options: {
            top_k: 20,
            offset: 0,
            semantic: true
        }
    };

    // Add explicit filters
    const priceMax = document.getElementById('priceMax').value;
    const bedrooms = document.getElementById('bedrooms').value;
    const unitType = document.getElementById('unitType').value;
    const mrtDistance = document.getElementById('mrtDistance').value;

    if (priceMax) request.filters.price_max = parseFloat(priceMax);
    if (bedrooms) request.filters.bedrooms = parseInt(bedrooms);
    if (unitType) request.filters.unit_type = unitType;
    if (mrtDistance) request.filters.mrt_distance_max = parseInt(mrtDistance);

    try {
        const response = await fetch(`${API_BASE}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(request)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        displayResults(data);
    } catch (error) {
        console.error('Search error:', error);
        alert('Search failed: ' + error.message);
    } finally {
        document.getElementById('loading').classList.add('hidden');
    }
}

// Display search results
function displayResults(data) {
    const resultsContainer = document.getElementById('results');
    const searchStats = document.getElementById('searchStats');
    const intentDisplay = document.getElementById('intentDisplay');
    const intentContent = document.getElementById('intentContent');
    const noResults = document.getElementById('noResults');

    // Show stats
    searchStats.textContent = `Found ${data.total} properties in ${data.took_ms}ms`;
    searchStats.classList.remove('hidden');

    // Show intent
    if (data.intent && data.intent.slots) {
        const slots = data.intent.slots;
        let intentText = [];
        
        if (slots.price_min || slots.price_max) {
            intentText.push(`💰 Price: ${formatPrice(slots.price_min)} - ${formatPrice(slots.price_max)}`);
        }
        if (slots.bedrooms) {
            intentText.push(`🛏️ Bedrooms: ${slots.bedrooms}`);
        }
        if (slots.unit_type) {
            intentText.push(`🏘️ Type: ${slots.unit_type}`);
        }
        if (slots.mrt_distance_max) {
            intentText.push(`🚇 MRT Distance: ≤${slots.mrt_distance_max}m`);
        }
        if (slots.location) {
            intentText.push(`📍 Location: ${slots.location}`);
        }
        if (data.intent.semantic_keywords && data.intent.semantic_keywords.length > 0) {
            intentText.push(`🔑 Keywords: ${data.intent.semantic_keywords.join(', ')}`);
        }

        if (intentText.length > 0) {
            intentContent.innerHTML = intentText.join('<br>');
            intentDisplay.classList.remove('hidden');
        }
    }

    // Show results or no results message
    if (data.results && data.results.length > 0) {
        resultsContainer.innerHTML = data.results.map(listing => createListingCard(listing)).join('');
        noResults.classList.add('hidden');
    } else {
        resultsContainer.innerHTML = '';
        noResults.classList.remove('hidden');
    }
}

// Create listing card HTML
function createListingCard(listing) {
    const price = listing.price ? `S$${listing.price.toLocaleString()}` : 'Price on request';
    const pricePerSqft = listing.price_per_sqft ? `S$${listing.price_per_sqft.toFixed(0)}/sqft` : '';
    const bedrooms = listing.bedrooms || '-';
    const bathrooms = listing.bathrooms || '-';
    const area = listing.area_sqft ? `${listing.area_sqft.toFixed(0)} sqft` : '-';
    const unitType = listing.unit_type || 'N/A';
    const location = listing.location || 'Location not specified';
    const mrt = listing.mrt_station ? `${listing.mrt_station} (${listing.mrt_distance_m}m)` : 'N/A';
    const title = listing.title || `Listing #${listing.listing_id}`;
    const score = (listing.score * 100).toFixed(0);
    const reasons = listing.matched_reasons ? listing.matched_reasons.join(' · ') : '';
    
    // Date formatting
    let listedInfo = '';
    if (listing.listed_date) {
        const date = new Date(listing.listed_date);
        const daysAgo = Math.floor((new Date() - date) / (1000 * 60 * 60 * 24));
        listedInfo = daysAgo === 0 ? 'Listed today' : `${daysAgo} days ago`;
    } else if (listing.listed_age) {
        listedInfo = listing.listed_age;
    }

    return `
        <div class="bg-white rounded-lg shadow-md overflow-hidden card-hover">
            <div class="p-6">
                <!-- Header -->
                <div class="flex justify-between items-start mb-3">
                    <h3 class="text-lg font-semibold text-gray-800 flex-1">${escapeHtml(title)}</h3>
                    <span class="ml-2 bg-purple-100 text-purple-800 text-xs font-semibold px-2.5 py-0.5 rounded">
                        ${score}% Match
                    </span>
                </div>

                <!-- Price -->
                <div class="mb-3">
                    <div class="text-2xl font-bold text-purple-600">${price}</div>
                    ${pricePerSqft ? `<div class="text-sm text-gray-500">${pricePerSqft}</div>` : ''}
                </div>

                <!-- Details -->
                <div class="grid grid-cols-3 gap-2 mb-3 text-sm">
                    <div class="text-center">
                        <div class="text-gray-500">Beds</div>
                        <div class="font-semibold">${bedrooms}</div>
                    </div>
                    <div class="text-center">
                        <div class="text-gray-500">Baths</div>
                        <div class="font-semibold">${bathrooms}</div>
                    </div>
                    <div class="text-center">
                        <div class="text-gray-500">Area</div>
                        <div class="font-semibold">${area}</div>
                    </div>
                </div>

                <!-- Type & Location -->
                <div class="mb-3 space-y-1 text-sm">
                    <div class="flex items-center text-gray-700">
                        <span class="mr-2">🏘️</span>
                        <span>${escapeHtml(unitType)}</span>
                    </div>
                    <div class="flex items-center text-gray-700">
                        <span class="mr-2">📍</span>
                        <span>${escapeHtml(location)}</span>
                    </div>
                    <div class="flex items-center text-gray-700">
                        <span class="mr-2">🚇</span>
                        <span>${escapeHtml(mrt)}</span>
                    </div>
                </div>

                <!-- Matched Reasons -->
                ${reasons ? `
                <div class="mb-3 p-2 bg-green-50 rounded text-xs text-green-700">
                    ✓ ${escapeHtml(reasons)}
                </div>
                ` : ''}

                <!-- Listed Date -->
                ${listedInfo ? `
                <div class="text-xs text-gray-500 mb-3">
                    📅 ${listedInfo}
                </div>
                ` : ''}

                <!-- Action Button -->
                <button 
                    onclick="viewDetails(${listing.listing_id})"
                    class="w-full bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded transition duration-200"
                >
                    View Details
                </button>
            </div>
        </div>
    `;
}

// View listing details
function viewDetails(listingId) {
    // Log feedback
    logFeedback(listingId, 'click');
    
    // Open in new tab (assuming PropertyGuru URL pattern)
    const url = `https://www.propertyguru.com.sg/listing/${listingId}`;
    window.open(url, '_blank');
}

// Log user feedback
async function logFeedback(listingId, action) {
    try {
        await fetch(`${API_BASE}/feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                search_id: 'web-search-' + Date.now(), // Simple search ID for demo
                listing_id: listingId,
                action: action
            })
        });
    } catch (error) {
        console.error('Failed to log feedback:', error);
    }
}

// Handle Enter key press in search input
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        search();
    }
}

// Format price
function formatPrice(price) {
    if (!price) return '';
    if (price >= 1000000) {
        return 'S$' + (price / 1000000).toFixed(1) + 'M';
    } else if (price >= 1000) {
        return 'S$' + (price / 1000).toFixed(0) + 'K';
    }
    return 'S$' + price.toLocaleString();
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Load example on page load
window.addEventListener('DOMContentLoaded', () => {
    // Placeholder is already set in HTML
});

