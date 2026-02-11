const { BetaAnalyticsDataClient } = require('@google-analytics/data');

/**
 * Analytics API for Nongor Bot
 * FETCES: Traffic, conversion funnel, and engagement metrics from GA4
 */

// Initialize client
const analyticsClient = new BetaAnalyticsDataClient({
    credentials: JSON.parse(process.env.GOOGLE_ANALYTICS_CREDENTIALS || '{}')
});

const GA4_PROPERTY_ID = process.env.GA4_PROPERTY_ID;
const BOT_API_KEY = process.env.BOT_API_KEY;

module.exports = async (req, res) => {
    // Security: Only allow bot to access
    const apiKey = req.headers['x-api-key'];
    if (apiKey !== BOT_API_KEY) {
        return res.status(401).json({ error: 'Unauthorized' });
    }

    try {
        if (!GA4_PROPERTY_ID || !process.env.GOOGLE_ANALYTICS_CREDENTIALS) {
            console.error('Missing GA4 credentials');
            return res.status(500).json({ error: 'Server misconfiguration' });
        }

        // 1. Fetch Today's Traffic Summary
        const [todayTraffic] = await analyticsClient.runReport({
            property: `properties/${GA4_PROPERTY_ID}`,
            dateRanges: [{ startDate: 'today', endDate: 'today' }],
            metrics: [
                { name: 'activeUsers' },
                { name: 'screenPageViews' },
                { name: 'sessions' },
                { name: 'bounceRate' },
                { name: 'averageSessionDuration' }
            ]
        });

        // 2. Fetch Conversion Funnel Data (Today)
        const [funnelData] = await analyticsClient.runReport({
            property: `properties/${GA4_PROPERTY_ID}`,
            dateRanges: [{ startDate: 'today', endDate: 'today' }],
            dimensions: [{ name: 'eventName' }],
            metrics: [{ name: 'eventCount' }],
            dimensionFilter: {
                orGroup: {
                    expressions: [
                        { filter: { fieldName: 'eventName', stringFilter: { value: 'view_item' } } },
                        { filter: { fieldName: 'eventName', stringFilter: { value: 'add_to_cart' } } },
                        { filter: { fieldName: 'eventName', stringFilter: { value: 'begin_checkout' } } },
                        { filter: { fieldName: 'eventName', stringFilter: { value: 'purchase' } } }
                    ]
                }
            }
        });

        // 3. Fetch Top Products by Views
        const [topPages] = await analyticsClient.runReport({
            property: `properties/${GA4_PROPERTY_ID}`,
            dateRanges: [{ startDate: 'today', endDate: 'today' }],
            dimensions: [{ name: 'pageTitle' }],
            metrics: [{ name: 'screenPageViews' }],
            limit: 5
        });

        // 4. Fetch Traffic Sources
        const [sources] = await analyticsClient.runReport({
            property: `properties/${GA4_PROPERTY_ID}`,
            dateRanges: [{ startDate: 'today', endDate: 'today' }],
            dimensions: [{ name: 'sessionSource' }],
            metrics: [{ name: 'sessions' }],
            limit: 5
        });

        // Format and return response
        const response = {
            today: {
                visitors: parseInt(todayTraffic.rows?.[0]?.metricValues?.[0]?.value || 0),
                pageViews: parseInt(todayTraffic.rows?.[0]?.metricValues?.[1]?.value || 0),
                sessions: parseInt(todayTraffic.rows?.[0]?.metricValues?.[2]?.value || 0),
                bounceRate: parseFloat(todayTraffic.rows?.[0]?.metricValues?.[3]?.value || 0).toFixed(2) + '%',
                avgSessionDuration: parseInt(todayTraffic.rows?.[0]?.metricValues?.[4]?.value || 0)
            },
            funnel: formatFunnel(funnelData.rows || []),
            topPages: topPages.rows?.map(r => ({
                title: r.dimensionValues[0].value,
                views: parseInt(r.metricValues[0].value)
            })) || [],
            trafficSources: formatSources(sources.rows || [])
        };

        res.status(200).json(response);

    } catch (error) {
        console.error('Analytics API Error:', error);
        res.status(500).json({
            error: 'Failed to fetch analytics',
            details: error.message
        });
    }
};

/** Helpers */
function formatFunnel(rows) {
    const counts = {
        view_item: 0,
        add_to_cart: 0,
        begin_checkout: 0,
        purchase: 0
    };

    rows.forEach(row => {
        const name = row.dimensionValues[0].value;
        counts[name] = parseInt(row.metricValues[0].value);
    });

    return {
        product_views: counts.view_item,
        add_to_cart: counts.add_to_cart,
        checkout_started: counts.begin_checkout,
        purchases: counts.purchase,
        view_to_cart_rate: counts.view_item ? ((counts.add_to_cart / counts.view_item) * 100).toFixed(1) : 0,
        cart_to_checkout_rate: counts.add_to_cart ? ((counts.begin_checkout / counts.add_to_cart) * 100).toFixed(1) : 0,
        checkout_to_purchase_rate: counts.begin_checkout ? ((counts.purchase / counts.begin_checkout) * 100).toFixed(1) : 0
    };
}

function formatSources(rows) {
    const sources = {};
    rows.forEach(row => {
        sources[row.dimensionValues[0].value] = parseInt(row.metricValues[0].value);
    });
    return sources;
}
