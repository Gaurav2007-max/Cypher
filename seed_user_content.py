"""
seed_user_content.py
====================
Populates all user-requested destinations, activities, cuisines, and stories
for Faridabad, Shimla, Agra, Jaipur, and Varanasi into the database.
Safe to run idempotently (checks for existing records by name).
"""
from datetime import datetime
from app import create_app
from app.extensions import db
from app.models import City, Destination, Activity, CuisineItem, Story

def populate_user_content(app=None):
    if app is None:
        app = create_app()
    with app.app_context():
        # Ensure cities exist
        cities = {c.name.lower(): c for c in City.query.all()}

        c_fbd = cities.get("faridabad")
        c_shimla = cities.get("shimla")
        c_agra = cities.get("agra")
        c_jaipur = cities.get("jaipur")
        c_varanasi = cities.get("varanasi")

        if not all([c_fbd, c_shimla, c_agra, c_jaipur, c_varanasi]):
            print("ERROR: One or more cities missing. Please ensure database has all 5 cities.")
            return False

        # ─── 1. DESTINATIONS ────────────────────────────────────────────────
        dest_specs = [
            # Faridabad
            {
                "city_id": c_fbd.id,
                "name": "DHYANKAKSH — Satyug Darshan Meditation Sanctuary",
                "category": "spiritual",
                "description": "A world-class meditation and spiritual destination at the Satyug Darshan campus in Greater Faridabad, Haryana. Known for its distinctive architecture, serenity, and focus on meditation, inner peace and self-awareness.",
                "latitude": 28.4350,
                "longitude": 77.3750,
                "image_url": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=1000&q=80",
                "historical_significance": "Spiritual retreat campus founded to promote universal harmony, self-realization, and ethical values across cultures.",
                "local_stories": "The acoustic design inside the meditation dome creates natural acoustic resonance allowing quiet meditation in profound stillness.",
                "opening_hours": "October–March: 10 AM–4 PM; April–September: 10 AM–5 PM (Entry Free)",
                "accessibility_info": "Ground-level ramps and manicured garden pathways with complete wheelchair accessibility.",
                "is_hidden_gem": True,
                "source_attribution": "Satyug Darshan Vasundhara Trust (+91 85950 70695)",
                "crowd_status": "Normal",
                "story": {
                    "title": "The Haven of Stillness and Self-Awareness",
                    "content": "Dhyankaksh at Satyug Darshan Vasundhara stands as an architectural tribute to silence and inner peace. Set amidst verdant lawns away from highway bustle, its harmonious geometric dome invites visitors to leave behind modern stress and discover mindfulness.",
                    "audio_text": "Welcome to Dhyankaksh. Take a deep breath and feel the tranquil quiet of this meditation sanctuary. Built with thoughtful acoustic harmony, this space invites you to reflect, slow down, and experience peaceful mindfulness.",
                    "audio_duration_seconds": 40,
                    "fun_facts": "The campus was engineered with natural solar ventilation to maintain cool meditation temperatures year-round."
                }
            },
            {
                "city_id": c_fbd.id,
                "name": "Town Park, Sector 12",
                "category": "nature",
                "description": "Faridabad's premier expansive urban green space. Enjoy a morning walk, jogging, yoga or a relaxed picnic. A good option for families and budget travellers.",
                "latitude": 28.3888,
                "longitude": 77.3197,
                "image_url": "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=1000&q=80",
                "historical_significance": "Planned during Faridabad's modern expansion as a central ecological breathing space for families and fitness enthusiasts.",
                "local_stories": "Locals gather by the thousands during festive evenings and morning walking clubs in the cool shade of mature trees.",
                "opening_hours": "Daily 5 AM–10 PM (Best time: 4–7 PM for a relaxed walk and evening atmosphere)",
                "accessibility_info": "Paved walking tracks and step-free park entrances; nearest metro is Bata Chowk (Violet Line).",
                "is_hidden_gem": False,
                "source_attribution": "Faridabad Municipal Corporation",
                "crowd_status": "Moderate",
                "story": {
                    "title": "The Green Heart of Faridabad",
                    "content": "Town Park in Sector 12 serves as the communal lung of Faridabad. With open rolling lawns, musical fountain plazas, and shaded gazebos, it provides generations of city dwellers a welcoming refuge from urban momentum.",
                    "audio_text": "Welcome to Town Park Sector 12. Whether you are here for an invigorating dawn jog or a relaxed evening stroll, listen to the chirping birds in the canopy and enjoy this verdant sanctuary in the heart of Haryana.",
                    "audio_duration_seconds": 38,
                    "fun_facts": "The park hosts one of the largest open-air yoga gatherings in Haryana every International Yoga Day."
                }
            },
            # Shimla
            {
                "city_id": c_shimla.id,
                "name": "Jakhoo Temple & Giant Hanuman Statue",
                "category": "spiritual",
                "description": "An important hilltop temple dedicated to Lord Hanuman, known for its religious significance, panoramic mountain views and large Hanuman statue (2–2.5 km from The Ridge).",
                "latitude": 31.1009,
                "longitude": 77.1843,
                "image_url": "https://images.unsplash.com/photo-1544735716-392fe2489ffa?auto=format&fit=crop&w=1000&q=80",
                "historical_significance": "Mythology recounts that Lord Hanuman rested here while flying to the Himalayas to bring the Sanjeevani herb during the Ramayana.",
                "local_stories": "Footprints preserved in marble within the temple are believed by devotees to be those of Lord Hanuman himself.",
                "opening_hours": "7:00 AM–8:00 PM daily (Free entry)",
                "accessibility_info": "Accessible in 5 minutes via the Jakhoo Ropeway from The Ridge, or by a 2.5 km scenic uphill mountain trail.",
                "is_hidden_gem": False,
                "source_attribution": "Shimla District Administration",
                "crowd_status": "Moderate",
                "story": {
                    "title": "The Guardian Peak of Lord Hanuman",
                    "content": "Standing on Jakhoo Hill, the highest point of Shimla, you are embraced by panoramic Himalayan vistas. The majestic 108-foot vermilion statue of Lord Hanuman towers over alpine deodar trees, overlooking the entire valley with timeless grace.",
                    "audio_text": "You are standing at Jakhoo Temple, the highest point in Shimla. Legend says Lord Hanuman rested on this very summit during his epic quest for the life-saving Sanjeevani herb. Look out toward the snow-capped Himalayan peaks visible on clear days.",
                    "audio_duration_seconds": 45,
                    "fun_facts": "At 108 feet, the Jakhoo Hanuman statue surpasses Rio's Christ the Redeemer in height!"
                }
            },
            {
                "city_id": c_shimla.id,
                "name": "Himachal State Museum (Chaura Maidan)",
                "category": "museum",
                "description": "Showcases the region's historical artefacts, traditional art, sculptures, miniature paintings and cultural objects on Museum Road, Chaura Maidan.",
                "latitude": 31.1042,
                "longitude": 77.1517,
                "image_url": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?auto=format&fit=crop&w=1000&q=80",
                "historical_significance": "Established in 1974 to protect and showcase Himalayan indigenous arts, archaeology, and numismatics.",
                "local_stories": "The building was once a private residence of British colonial officials before its transformation into a sanctuary of Himalayan heritage.",
                "opening_hours": "10:00 AM–5:00 PM (Closed Mondays & gazetted holidays; Indian ₹50, Foreign ₹150, Children below 10: ₹30)",
                "accessibility_info": "Paved museum grounds; ground floor galleries are wheelchair accessible.",
                "is_hidden_gem": True,
                "source_attribution": "Department of Language & Culture, Himachal Pradesh",
                "crowd_status": "Normal",
                "story": {
                    "title": "Treasures of the Himalayan Valleys",
                    "content": "Step inside this colonial haven on Chaura Maidan to discover miniature paintings from the Kangra school, ancient stone deities carved in the 8th century, and intricate silver tribal jewellery.",
                    "audio_text": "Welcome to the Himachal State Museum. Here you will see centuries of mountain craftsmanship, from delicate Kangra miniature paintings to ancient bronze statues carved high in the Himalayan valleys.",
                    "audio_duration_seconds": 40,
                    "fun_facts": "The museum houses a rare collection of ancient coins dating back to the Mauryan and Kushan empires."
                }
            },
            {
                "city_id": c_shimla.id,
                "name": "Gaiety Heritage Cultural Complex",
                "category": "heritage",
                "description": "A historic Victorian theatre and cultural centre on Mall Road / Middle Bazar, associated with Shimla's performing arts and social history.",
                "latitude": 31.1048,
                "longitude": 77.1738,
                "image_url": "https://images.unsplash.com/photo-1514306191717-452ec28c7814?auto=format&fit=crop&w=1000&q=80",
                "historical_significance": "Iconic cultural venue of the Raj era where luminaries such as Rudyard Kipling, Baden-Powell, and K.L. Saigal graced the stage.",
                "local_stories": "Built with paper-mâché acoustic ceilings imported from England, providing flawless natural acoustic amplification without microphones.",
                "opening_hours": "11:00 AM–1:15 PM and 1:45 PM–7:00 PM (or 10:00 AM–5:00 PM; Indian ₹10, Foreign ₹25)",
                "accessibility_info": "Direct step-free entrance from Mall Road pedestrian promenade.",
                "is_hidden_gem": False,
                "source_attribution": "Gaiety Heritage Cultural Complex Trust",
                "crowd_status": "Normal",
                "story": {
                    "title": "Echoes of the Victorian Stage",
                    "content": "Gaiety Theatre is one of the world's very few surviving authentic Victorian theatres. Constructed in 1887, its horseshoe-shaped auditorium with gilded papier-mâché ornamentation has hosted historic plays, opera, and classical recitals for over a century.",
                    "audio_text": "You are standing inside the historic Gaiety Theatre on Mall Road. Notice the intricate gilded balconies and wooden proscenium. For over 130 years, this stage has witnessed legendary theatrical performances in the heart of Shimla.",
                    "audio_duration_seconds": 42,
                    "fun_facts": "Rudyard Kipling made some of his earliest stage appearances here while serving as a young journalist in Shimla."
                }
            },
            # Varanasi
            {
                "city_id": c_varanasi.id,
                "name": "Kashi Vishwanath Temple (Golden Temple)",
                "category": "spiritual",
                "description": "One of the most important Shiva temples in India, attracting pilgrims throughout the year. The surrounding temple corridor and lanes provide a glimpse of the religious life of the old city.",
                "latitude": 25.3109,
                "longitude": 83.0107,
                "image_url": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?auto=format&fit=crop&w=1000&q=80",
                "historical_significance": "Ancient spiritual core of Varanasi, reconstructed by Queen Ahilyabai Holkar of Indore in 1780 CE.",
                "local_stories": "Varanasi folklore holds that the holy city rests upon the trident of Lord Shiva, making it eternal and spiritually transcendent.",
                "opening_hours": "03:00 AM – 11:00 PM (Allow 1–2 hours, possibly longer with queues)",
                "accessibility_info": "Vishwanath Dham Corridor features ramps, golf carts for senior citizens, and level marble plazas.",
                "is_hidden_gem": False,
                "source_attribution": "Kashi Vishwanath Temple Trust",
                "crowd_status": "Crowded",
                "story": {
                    "title": "The Golden Spires of Mahadev",
                    "content": "Standing in the sacred corridor of Kashi Vishwanath, you are at the spiritual crossroads of eternal Varanasi. Crowned with nearly a ton of gold leaf donated by Maharaja Ranjit Singh, the sanctum reverberates with timeless devotion.",
                    "audio_text": "Welcome to Kashi Vishwanath. Listen to the resonant bells echoing across the holy corridor. Dedicated to Lord Shiva, this sacred sanctuary has drawn seekers, saints, and travelers for millennia.",
                    "audio_duration_seconds": 45,
                    "fun_facts": "The golden spires of the temple were gilded using genuine gold leaf contributed by Punjab ruler Maharaja Ranjit Singh in 1835."
                }
            }
        ]

        dest_map = {}
        for spec in dest_specs:
            story_spec = spec.pop("story", None)
            existing = Destination.query.filter_by(name=spec["name"]).first()
            if not existing:
                existing = Destination(**spec)
                db.session.add(existing)
                db.session.flush()
            else:
                for k, v in spec.items():
                    setattr(existing, k, v)
                db.session.flush()
            dest_map[existing.name] = existing

            if story_spec:
                existing_story = Story.query.filter_by(destination_id=existing.id).first()
                if not existing_story:
                    s = Story(destination_id=existing.id, **story_spec)
                    db.session.add(s)
                else:
                    for k, v in story_spec.items():
                        setattr(existing_story, k, v)

        # ─── 2. ACTIVITIES ──────────────────────────────────────────────────
        act_specs = [
            # Agra
            {
                "city_id": c_agra.id,
                "name": "Explore Local Handicrafts & Marble Inlay Bazaars",
                "category": "shopping_walk",
                "description": "Browse for marble inlay work, leather goods, embroidered textiles, souvenirs and sweets. Visit a genuine artisan workshop to understand how tiny pieces of coloured stone are cut and set into marble. Where: Sadar Bazaar, Kinari Bazaar. Tip: Compare prices between shops and agree on the price before buying.",
                "price_range": "Free to browse; shopping costs extra",
                "typical_duration": "Allow 1–2 hours",
                "recommended_time": "Afternoon / Evening (03:00 PM – 07:00 PM)",
                "safety_precautions": "Compare prices between shops and agree on price before buying.",
                "price_source": "Sadar Bazaar & Kinari Bazaar Artisans",
                "image_url": "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_agra.id,
                "name": "Take a Half-Day Trip to Fatehpur Sikri",
                "category": "heritage_trip",
                "description": "About an hour from Agra by road, this historic Mughal city has monumental gateways, palace complexes and courtyards. See Buland Darwaza and the architectural blend of different traditions. Best for: Anyone interested in Mughal history and heritage photography.",
                "price_range": "Transport and entry extra",
                "typical_duration": "Allow 3–5 hours including travel",
                "recommended_time": "Morning (08:00 AM – 01:00 PM)",
                "safety_precautions": "Confirm travel and entry arrangements before leaving the city.",
                "price_source": "Archaeological Survey of India published tariffs",
                "image_url": "https://images.unsplash.com/photo-1590766940554-634a7ed41450?auto=format&fit=crop&w=800&q=80"
            },
            # Varanasi
            {
                "city_id": c_varanasi.id,
                "name": "Attend Evening Ganga Aarti at Dashashwamedh Ghat",
                "category": "cultural_ritual",
                "description": "Priests perform synchronised rituals with large lamps, incense, bells and devotional music beside the river. The atmosphere grows increasingly vibrant as the sky darkens and crowds gather. Arrive early for a good view or book a boat beforehand.",
                "price_range": "Free to view (Boat hire extra)",
                "typical_duration": "1.5–2 hours",
                "recommended_time": "Evening (Dusk)",
                "safety_precautions": "Arrive early for a good view; book boat with reputable operator and confirm price beforehand.",
                "price_source": "Varanasi Ghat Administration",
                "image_url": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_varanasi.id,
                "name": "Visit Kashi Vishwanath Temple",
                "category": "spiritual",
                "description": "One of the most important Shiva temples in India, attracting pilgrims throughout the year. Dress respectfully, follow security instructions and check current entry rules. Keep extra time for queues and leave restricted belongings outside as instructed.",
                "price_range": "Free entry (Special darshan optional extra)",
                "typical_duration": "Allow 1–2 hours, possibly longer with queues",
                "recommended_time": "Morning or Afternoon",
                "safety_precautions": "Dress respectfully; follow security instructions; leave restricted belongings in lockers outside.",
                "price_source": "Kashi Vishwanath Temple Administration",
                "image_url": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?auto=format&fit=crop&w=800&q=80"
            },
            # Jaipur
            {
                "city_id": c_jaipur.id,
                "name": "Shop in Johari Bazaar and Bapu Bazaar",
                "category": "shopping_walk",
                "description": "Johari Bazaar is associated with jewellery, gemstones and traditional ornaments, while Bapu Bazaar is popular for textiles, mojari footwear, bags and souvenirs. Walk through the colourful lanes, compare items in several shops and stop for kachori or sweets.",
                "price_range": "Shopping budget depends on you",
                "typical_duration": "Allow 1.5–3 hours",
                "recommended_time": "Late Afternoon (04:00 PM – 08:00 PM)",
                "safety_precautions": "Compare items in several shops and agree on price before buying.",
                "price_source": "Jaipur City Bazaar Traders",
                "image_url": "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_jaipur.id,
                "name": "Watch the Sunset from Nahargarh Fort",
                "category": "sightseeing_excursion",
                "description": "The fort sits high above the city on the Aravalli hills. Its elevated position gives you a broad view of Jaipur's rooftops and cityscape. Explore historic palace rooms and find a suitable viewpoint for sunset. Best for panoramic photography.",
                "price_range": "Entry and transport extra",
                "typical_duration": "Allow 1.5–2.5 hours including travel",
                "recommended_time": "Evening (Before dusk)",
                "safety_precautions": "Arrange return transport in advance, particularly if staying until dusk.",
                "price_source": "Department of Archaeology & Museums, Rajasthan",
                "image_url": "https://images.unsplash.com/photo-1599661046289-e31897846e41?auto=format&fit=crop&w=800&q=80"
            },
            # Shimla
            {
                "city_id": c_shimla.id,
                "name": "Jakhoo Ropeway ride",
                "category": "ropeway_adventure",
                "description": "Enjoy a scenic gondola ride between the Ridge area and Jakhoo Hill, with panoramic views of Shimla and surrounding mountains. Lower station near The Ridge, upper close to Jakhoo Temple.",
                "price_range": "Approximately ₹500–₹600 round trip",
                "typical_duration": "Approximately 5 minutes each way",
                "recommended_time": "Usually 9:30 AM until sunset, depending on weather",
                "safety_precautions": "Follow cabin crew instructions; operations depend on mountain weather.",
                "price_source": "Jakhoo Ropeway Operating Authority",
                "image_url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_shimla.id,
                "name": "Horse riding in Kufri",
                "category": "mountain_riding",
                "description": "Explore mountain trails and viewpoints near Kufri on horseback, subject to local conditions and operator availability. Trail towards Mahasu Peak, around 16–20 km from Shimla.",
                "price_range": "Approximately ₹500–₹700 per person round trip",
                "typical_duration": "1.5–2 hours",
                "recommended_time": "Morning / Mid-day",
                "safety_precautions": "Prices vary by route, season and operator, so confirm before riding.",
                "price_source": "Kufri Horse Operators Union",
                "image_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_shimla.id,
                "name": "Snow activities in Kufri",
                "category": "snow_sports",
                "description": "During suitable winter conditions, visitors can enjoy snow play and selected snow-based activities. Timings: 8:30 AM–7:30 PM. Session: 15 minutes to get ready, followed by 45 minutes inside. Phone: +91 93171 92601",
                "price_range": "₹400–₹800 per session",
                "typical_duration": "1 hour (15m prep + 45m inside)",
                "recommended_time": "8:30 AM–7:30 PM (Winter)",
                "safety_precautions": "Availability depends on snowfall and weather. Wear warm winter gear.",
                "price_source": "Kufri Snow Venue (+91 93171 92601)",
                "image_url": "https://images.unsplash.com/photo-1517048676732-d65bc937f952?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_shimla.id,
                "name": "Experience Himachali folk culture",
                "category": "cultural_performance",
                "description": "Watch traditional Nati folk dance, enjoy traditional folk music, and taste authentic Himachali cuisine at cultural festivals or special events when available.",
                "price_range": "Free at public festivals / ₹200–₹400 for events",
                "typical_duration": "1.5 hours",
                "recommended_time": "Evening",
                "safety_precautions": "Family-friendly cultural showcase.",
                "price_source": "Himachal Tourism Department",
                "image_url": "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_shimla.id,
                "name": "Shop at Mall Road and Lakkar Bazaar",
                "category": "shopping_walk",
                "description": "Buy woollen shawls, Himachali caps, wooden handicrafts and souvenirs while exploring the town's lively markets without vehicle traffic.",
                "price_range": "Free to browse; shopping costs extra",
                "typical_duration": "2–3 hours",
                "recommended_time": "Afternoon / Evening",
                "safety_precautions": "Pedestrian-only promenade; comfortable walking shoes recommended.",
                "price_source": "Mall Road & Lakkar Bazaar Merchants",
                "image_url": "https://images.unsplash.com/photo-1472851294608-062f824d29cc?auto=format&fit=crop&w=800&q=80"
            }
        ]

        for spec in act_specs:
            existing = Activity.query.filter_by(name=spec["name"]).first()
            if not existing:
                existing = Activity(**spec)
                db.session.add(existing)
            else:
                for k, v in spec.items():
                    setattr(existing, k, v)

        # ─── 3. CUISINE ITEMS ───────────────────────────────────────────────
        cuisine_specs = [
            # Faridabad
            {
                "city_id": c_fbd.id,
                "name": "Chole Kulche - Faridabad street food",
                "description": "Spicy chickpeas with soft kulche, onion lemon, chutney. A great local breakfast or lunch.",
                "cultural_background": "Everyday staple street-food across Faridabad and NCR.",
                "dietary_tags": "vegetarian,street-food,breakfast",
                "allergen_info": "Contains wheat gluten and legumes.",
                "price_range": "₹150-200",
                "famous_spots": "Kashyap chole kulche - sector 21C, NIT",
                "user_rating": 4.8,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_fbd.id,
                "name": "Rajwada bhog",
                "description": "A vegetarian thali - style meal with a variety of dishes, ideal for experiencing a traditional Indian spread.",
                "cultural_background": "Celebration of traditional Indian vegetarian hospitality and thali dining.",
                "dietary_tags": "vegetarian,thali,family-dining",
                "allergen_info": "Contains dairy (ghee/paneer) and wheat gluten.",
                "price_range": "₹400-700",
                "famous_spots": "Pacific Mall, sector 20B",
                "user_rating": 4.9,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_fbd.id,
                "name": "Malai Chaap & Tandoori Snacks",
                "description": "Creamy or spicy grilled soya chaap with chutney & rumali roti is a popular NCR- style treat.",
                "cultural_background": "Modern NCR culinary sensation that has become a staple of evening social life.",
                "dietary_tags": "vegetarian,tandoor,street-food",
                "allergen_info": "Contains soya, dairy (cream/butter), and wheat gluten.",
                "price_range": "₹100-200",
                "famous_spots": "Sector 19, Sector 37, NIT",
                "user_rating": 4.8,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=800&q=80"
            },
            # Agra
            {
                "city_id": c_agra.id,
                "name": "Bedai and aloo sabzi",
                "description": "A popular local breakfast consisting of a crisp, puffed, deep fried bread called bedai, served with spicy potato curry. It is often eaten with jalebi, giving you a combination of spicy, savoury and sweet flavours.",
                "cultural_background": "Centuries-old breakfast ritual in old Agra, savoured hot from morning tawas.",
                "dietary_tags": "vegetarian,breakfast,street-food",
                "allergen_info": "Contains wheat gluten.",
                "price_range": "₹40-100",
                "famous_spots": "Belanganj, Rawatpura, Raja Mandi",
                "user_rating": 4.8,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_agra.id,
                "name": "Mughlai cuisine",
                "description": "Expect rich gravies, aromatic spices, slow-cooked meat, kebabs, biryani and breads such as naan. Chicken korma and kebabs are good starting points for a hearty meal. Vegetarian Mughlai-style gravies are also available. Best experience: Order a curry with naan or rice and share a second dish with your group.",
                "cultural_background": "Imperial banquet culinary tradition crafted for the Mughal court in Agra.",
                "dietary_tags": "mughlai,royal-heritage,non-veg,vegetarian-options",
                "allergen_info": "Contains nuts (cashew paste) and dairy (cream/ghee).",
                "price_range": "₹180-450",
                "famous_spots": "Sadar Bazaar, Taj Ganj and the Fatehabad Road restaurant belt",
                "user_rating": 4.9,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1545247181-516773ca83e3?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_agra.id,
                "name": "Kebabs and chicken rolls",
                "description": "Grilled or pan-cooked kebabs seasoned with spices and often served with mint chutney and onions. Rolls make a convenient, less expensive option when you're sightseeing.",
                "cultural_background": "Agra's vibrant evening culinary culture around bazaar promenades.",
                "dietary_tags": "non-veg,street-food,quick-bite",
                "allergen_info": "Contains wheat gluten and egg.",
                "price_range": "₹80–250 for rolls or kebab portions",
                "famous_spots": "Mama Chicken Mama Franky House in Sadar Bazaar, Agra Cantt food market",
                "user_rating": 4.7,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1529006557810-274b9b2fc783?auto=format&fit=crop&w=800&q=80"
            },
            # Varanasi
            {
                "city_id": c_varanasi.id,
                "name": "Kachori-sabzi",
                "description": "A classic Banarasi breakfast of crisp kachori filled or flavoured with spices, served with hot potato or chickpea curry. It is filling, inexpensive and often eaten standing at a small shop in the morning.",
                "cultural_background": "Morning ritual for Banarasis following a dip in the holy river Ganga.",
                "dietary_tags": "vegetarian,breakfast,street-food",
                "allergen_info": "Contains wheat gluten and legumes.",
                "price_range": "₹30–80 per plate",
                "famous_spots": "Neelu Kachori Bhandar in old-city Kachori Gali, Chowk, Godowlia, Dashashwamedh lanes",
                "user_rating": 4.9,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_varanasi.id,
                "name": "Banarasi tamatar chaat",
                "description": "A distinctive local snack made with cooked tomatoes, potatoes, spices and chutneys, often finished with crunchy toppings. Tangy, savoury and spicy, with a softer texture than many other chaats.",
                "cultural_background": "Unique to Kashi, invented by the city's legendary chaat walas.",
                "dietary_tags": "vegetarian,street-food,spicy",
                "allergen_info": "Contains ghee and cashews.",
                "price_range": "₹40–100 per serving",
                "famous_spots": "Kashi Chat Bhandar, Deena Chaat Bhandar, Godowlia, Dashashwamedh Road",
                "user_rating": 4.9,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_varanasi.id,
                "name": "Banarasi lassi",
                "description": "Thick yoghurt blended with sugar, sometimes topped with cream or malai. Cooling, rich and filling—particularly enjoyable after a morning walk through the old city. Tip: If eating several snacks, order one lassi to share.",
                "cultural_background": "Iconic traditional beverage of Varanasi, churned fresh in copper pots.",
                "dietary_tags": "vegetarian,dessert,beverage",
                "allergen_info": "Contains dairy (curd, malai, rabri).",
                "price_range": "₹40–100 per glass or kulhad",
                "famous_spots": "Blue Lassi Shop, Pahalwan Lassi, Godowlia, Chowk and lanes around main temple district",
                "user_rating": 4.9,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1571006682855-3fc35088e7a3?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_varanasi.id,
                "name": "Banarasi paan",
                "description": "A betel leaf folded around a filling that can include fennel, sweet preserves, coconut and other ingredients. Sweet paan is a popular after-meal tradition and a recognisable part of Banaras culture. Tip: Ask for meetha paan if you prefer a sweet version.",
                "cultural_background": "Immortalized in Indian songs and folklore as the pinnacle of hospitality.",
                "dietary_tags": "vegetarian,digestive,traditional",
                "allergen_info": "Specify tobacco-free meetha paan; optionally contains areca nut.",
                "price_range": "₹20–80 per paan, depending on ingredients",
                "famous_spots": "Godowlia, Lanka, Chowk and around old-city markets",
                "user_rating": 4.9,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=800&q=80"
            },
            # Jaipur
            {
                "city_id": c_jaipur.id,
                "name": "Dal baati churma",
                "description": "This is Rajasthan's signature meal: baked wheat balls called baati, served with lentil dal and sweet, crumbled churma. The baati is often broken and dipped in ghee before eating. A complete, hearty meal.",
                "cultural_background": "Warrior dish engineered by Rajputs for desert sustenance.",
                "dietary_tags": "vegetarian,royal-heritage,traditional",
                "allergen_info": "Contains wheat gluten and dairy (ghee).",
                "price_range": "₹180–400 per person; elaborate thalis ₹400–700+",
                "famous_spots": "Rajasthani Thali Dal Bati Churma in Bani Park, MI Road, C-Scheme",
                "user_rating": 4.9,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1610057099443-fde8c4d50f91?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_jaipur.id,
                "name": "Pyaaz kachori",
                "description": "A deep-fried pastry filled with spiced onions. It is crisp outside, soft inside and often served with chutney. It makes a popular breakfast or snack, particularly with a cup of chai. Best experience: Eat it freshly fried.",
                "cultural_background": "Beloved breakfast and afternoon snack of the Pink City.",
                "dietary_tags": "vegetarian,breakfast,street-food",
                "allergen_info": "Contains wheat gluten.",
                "price_range": "₹25–60 each",
                "famous_spots": "Johari Bazaar, Bapu Bazaar, MI Road and old walled city snack shops",
                "user_rating": 4.9,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_jaipur.id,
                "name": "Gatte ki sabzi and ker sangri",
                "description": "Gatte ki sabzi features gram-flour dumplings cooked in a spiced yoghurt-based gravy. Ker sangri is a distinctive desert dish made with locally associated dried berries and beans. Best experience: Order with bajra roti or a Rajasthani thali.",
                "cultural_background": "Traditional Marwari culinary innovation utilizing dried desert produce.",
                "dietary_tags": "vegetarian,authentic,marwari",
                "allergen_info": "Contains gram flour and dairy (yoghurt).",
                "price_range": "₹150–350 per dish; ₹250–500 for a meal",
                "famous_spots": "Traditional Rajasthani restaurants in Bani Park, MI Road and C-Scheme",
                "user_rating": 4.8,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=800&q=80"
            },
            # Shimla
            {
                "city_id": c_shimla.id,
                "name": "Chha Gosht",
                "description": "A traditional Himachali mutton curry prepared with yoghurt, gram flour and spices.",
                "cultural_background": "Highland delicacy of the Himachal hills, prepared for celebrations and cold seasons.",
                "dietary_tags": "non-veg,pahari-heritage,specialty",
                "allergen_info": "Contains dairy (yoghurt) and gram flour.",
                "price_range": "₹250–₹450",
                "famous_spots": "Himachali Rasoi (54, Mall Road, Middle Bazaar)",
                "user_rating": 4.9,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1545247181-516773ca83e3?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_shimla.id,
                "name": "Himachali Dham",
                "description": "A traditional festive meal served at weddings and special occasions. It usually includes rice, dal, madra and other regional dishes.",
                "cultural_background": "Hereditary community feast cooked in brass vessels without onion or garlic.",
                "dietary_tags": "vegetarian,dham,royal-heritage",
                "allergen_info": "Contains dairy (curd/ghee) and legumes.",
                "price_range": "₹200–₹500 per thali",
                "famous_spots": "Himachali Rasoi (54, Mall Road, Middle Bazaar), Rattan Dhaba (Knollswood, Chhota Shimla)",
                "user_rating": 4.9,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=800&q=80"
            },
            {
                "city_id": c_shimla.id,
                "name": "Babru",
                "description": "A Himachali snack made from wheat dough stuffed with black gram paste and deep-fried. It is often eaten with tamarind chutney.",
                "cultural_background": "Traditional morning mountain snack providing energy in cold hill weather.",
                "dietary_tags": "vegetarian,breakfast,street-food",
                "allergen_info": "Contains wheat gluten and legumes.",
                "price_range": "₹40–₹100",
                "famous_spots": "Goofa Ashiana Restaurant (The Ridge, Shimla)",
                "user_rating": 4.8,
                "verified_status": "verified",
                "image_url": "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=800&q=80"
            }
        ]

        for spec in cuisine_specs:
            existing = CuisineItem.query.filter_by(name=spec["name"]).first()
            if not existing:
                existing = CuisineItem(**spec)
                db.session.add(existing)
            else:
                for k, v in spec.items():
                    setattr(existing, k, v)

        db.session.commit()
        return True

if __name__ == "__main__":
    populate_user_content()
