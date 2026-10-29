from datetime import datetime, timedelta
import os
from app import create_app
from app.extensions import db
from app.models import (
    User, UserProfile, EmergencyContact, City, Destination, Story,
    Activity, CuisineItem, TransportOption
)

def seed(app=None):
    app = app or create_app()
    with app.app_context():
        db.create_all()
        if User.query.count() or City.query.count():
            print("Database already contains application data; skipping demo seed to preserve existing records.")
            return False

        seed_demo_users = os.getenv('SEED_DEMO_USERS', 'true').lower() in ('true', '1', 'yes')
        tourist_profile = None
        authority = None
        if seed_demo_users:
            print("Creating local demo users...")
            admin = User(
                username='admin',
                email='admin@traveltech.gov.in',
                role='admin',
                authority_approved=True
            )
            admin.set_password('admin123')

            authority = User(
                username='officer_sharma',
                email='sharma@haryanatourism.gov.in',
                role='authority',
                authority_approved=True
            )
            authority.set_password('authority123')

            pending_auth = User(
                username='officer_verma',
                email='verma@uptourism.gov.in',
                role='authority',
                authority_approved=False
            )
            pending_auth.set_password('authority123')

            tourist = User(
                username='alex_traveler',
                email='alex.traveler@example.com',
                role='tourist',
                authority_approved=False
            )
            tourist.set_password('tourist123')
            db.session.add_all([admin, authority, pending_auth, tourist])
            db.session.flush()

            tourist_profile = UserProfile(
                user_id=tourist.id,
                full_name='Alex Rivera',
                nationality='International / Explorer',
                phone='+91 98765 43210',
                emergency_consent=False,
                sensor_consent=False,
                location_tracking_enabled=False,
                audio_speech_rate=1.0,
                proximity_radius_meters=50
            )
            db.session.add(tourist_profile)
            db.session.add(EmergencyContact(
                user_id=tourist.id,
                name='Global Care Travel Assistance',
                email='emergency.desk@globalcare-assist.com',
                phone='+1 800 555 0199',
                relationship='Travel Assistance Agency',
                is_agency=True,
                is_primary=True
            ))
        else:
            print("Skipping demo accounts; seeding sample travel content only.")

        print("Seeding Cities...")
        # Cities
        c_fbd = City(
            name='Faridabad',
            state='Haryana',
            country='India',
            latitude=28.4089,
            longitude=77.3178,
            image_url='https://upload.wikimedia.org/wikipedia/commons/thumb/7/78/Nahar_Singh_Palace%2C_Ballabhgarh.jpg/1920px-Nahar_Singh_Palace%2C_Ballabhgarh.jpg',
            description='Industrial powerhouse rich in 10th-century Tomar Rajput reservoirs, Aravalli biodiversity, and heritage craftsmanship.'
        )
        c_shimla = City(
            name='Shimla',
            state='Himachal Pradesh',
            country='India',
            latitude=31.1048,
            longitude=77.1734,
            image_url='https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?auto=format&fit=crop&w=1200&q=80',
            description='Queen of the Hills featuring colonial neo-gothic architecture, snow-clad Himalayan ridges, and apple orchards.'
        )
        c_agra = City(
            name='Agra',
            state='Uttar Pradesh',
            country='India',
            latitude=27.1767,
            longitude=78.0081,
            image_url='https://images.unsplash.com/photo-1564507592333-c60657eea523?auto=format&fit=crop&w=1200&q=80',
            description='Eternal city of love on the Yamuna river, boasting three iconic UNESCO World Heritage wonders.'
        )
        c_jaipur = City(
            name='Jaipur',
            state='Rajasthan',
            country='India',
            latitude=26.9124,
            longitude=75.7873,
            image_url='https://images.unsplash.com/photo-1599661046289-e31897846e41?auto=format&fit=crop&w=1200&q=80',
            description='The Pink City with magnificent sandstone fortresses, royal observatories, and vibrant bazaars.'
        )
        c_varanasi = City(
            name='Varanasi',
            state='Uttar Pradesh',
            country='India',
            latitude=25.3176,
            longitude=82.9739,
            image_url='https://images.unsplash.com/photo-1561361513-2d000a50f0dc?auto=format&fit=crop&w=1200&q=80',
            description='One of the world’s oldest living cities, spiritual sanctum of sacred Ganga ghats and evening aarti rituals.'
        )
        db.session.add_all([c_fbd, c_shimla, c_agra, c_jaipur, c_varanasi])
        db.session.flush()

        if tourist_profile:
            tourist_profile.preferred_city_id = c_fbd.id

        print("Seeding Faridabad Destinations & Stories...")
        # Faridabad Destinations
        d_surajkund = Destination(
            city_id=c_fbd.id,
            name='Surajkund Ancient Amphitheater & Reservoir',
            category='heritage',
            description='An ancient 10th-century semi-circular sun amphitheatre and stepped reservoir built by King Suraj Pal of the Tomar dynasty in the Aravalli hills.',
            latitude=28.4870,
            longitude=77.2831,
            image_url='https://images.unsplash.com/photo-1596401057633-54a8fe8ef647?auto=format&fit=crop&w=1000&q=80',
            historical_significance='Constructed in 10th century CE by Tomar rulers prior to the establishment of Delhi; historically dedicated to the Sun God (Surya).',
            local_stories='Legend holds that early Tomar kings held sacred water offerings here facing the sunrise, with stepped embankments designed to mirror the rays of the sun.',
            opening_hours='06:00 AM - 07:00 PM',
            accessibility_info='Stone ramp access to upper amphitheater terrace; lower steps require care.',
            is_hidden_gem=False,
            source_attribution='Archaeological Survey of India & Haryana Tourism',
            last_verified_at=datetime.utcnow(),
            crowd_status='Normal',
            crowd_updated_at=datetime.utcnow(),
            crowd_expires_at=None,
            crowd_explanation=None,
            crowd_updated_by_id=authority.id if authority else None
        )

        d_nahar_singh = Destination(
            city_id=c_fbd.id,
            name='Raja Nahar Singh Palace (Ballabhgarh Fort)',
            category='heritage',
            description='A 1739 CE royal sandstone palace featuring intricately carved arched courtyards, jharokhas, and minarets commemorating the 1857 Martyr King Nahar Singh.',
            latitude=28.3414,
            longitude=77.3228,
            image_url='https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?auto=format&fit=crop&w=1000&q=80',
            historical_significance='Historic fortress home of legendary Jat ruler Raja Nahar Singh who valiantly resisted the British during the 1857 Indian Uprising.',
            local_stories='Underground tunnels were said to secretly connect Ballabhgarh Fort directly to Delhi’s Red Fort to safely ferry rebels during the war of independence.',
            opening_hours='09:00 AM - 06:00 PM',
            accessibility_info='Courtyard is wheelchair-friendly with ground level entrance.',
            is_hidden_gem=True,
            source_attribution='Haryana State Heritage Board',
            last_verified_at=datetime.utcnow(),
            crowd_status='Normal',
            crowd_updated_at=datetime.utcnow() - timedelta(hours=2),
            crowd_explanation='Pleasant visiting conditions, uncrowded royal galleries.'
        )

        d_badkhal = Destination(
            city_id=c_fbd.id,
            name='Badkhal Lake & Eco Biodiversity Ridge',
            category='nature',
            description='Scenic natural lake valley nestled within the Aravalli hills, renowned for winter migratory birds and tranquil sunset nature trails.',
            latitude=28.4180,
            longitude=77.2796,
            image_url='https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=1000&q=85',
            historical_significance='Constructed shortly after Indian independence in 1947 by damming two hillocks to support agricultural irrigation and bird habitats.',
            local_stories='Old shepherd tales describe peacocks gathering here at twilight as dusk falls over the rocky ridge cliffs.',
            opening_hours='Open 24 Hours (Daylight recommended)',
            accessibility_info='Ridge trail is uneven dirt track; viewpoint promenade is paved.',
            is_hidden_gem=False,
            source_attribution='Haryana Forest & Wildlife Department',
            last_verified_at=datetime.utcnow(),
            crowd_status='Moderate',
            crowd_updated_at=datetime.utcnow() - timedelta(hours=1),
            crowd_explanation='Family visitors along the promenade.'
        )

        d_asola = Destination(
            city_id=c_fbd.id,
            name='Asola Bhatti Sanctuary — Peacock Hidden Lake',
            category='nature',
            description='A turquoise hidden lake formed inside deep quartzite quarries surrounded by lush thorny scrub forests and wildlife sanctuaries.',
            latitude=28.4715,
            longitude=77.2512,
            image_url='https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1000&q=85',
            historical_significance='Former quarry site restored naturally by rainwater collection, now home to nilgai, golden jackals, and over 190 bird species.',
            local_stories='Local environmentalists regard this as the emerald lung of Faridabad, hidden away from industrial city noise.',
            opening_hours='06:30 AM - 05:00 PM (Requires entry permit at gate)',
            accessibility_info='Nature trek involves moderate incline on rocky path.',
            is_hidden_gem=True,
            source_attribution='Conservation Foundation & Eco-Tourism Cell',
            last_verified_at=datetime.utcnow(),
            crowd_status='Normal',
            crowd_updated_at=datetime.utcnow() - timedelta(hours=3),
            crowd_explanation='Pristine quiet nature trail.'
        )

        d_iskcon_fbd = Destination(
            city_id=c_fbd.id,
            name='Sri Sri Radha Govind Temple (ISKCON Faridabad)',
            category='spiritual',
            description='Majestic marble spiritual sanctuary featuring classical Vedic architecture, tranquil meditation halls, and evening musical kirtans.',
            latitude=28.4116,
            longitude=77.3112,
            image_url='https://upload.wikimedia.org/wikipedia/commons/d/d2/Iskcon_Delhi_Temple.jpg',
            historical_significance='Cultural and spiritual epicentre promoting non-violence, ethical living, and traditional devotional arts in the NCR region.',
            local_stories='Devotees celebrate the flower holi festival with fragrant rose petals showered from high temple balconies.',
            opening_hours='04:30 AM - 01:00 PM, 04:30 PM - 08:30 PM',
            accessibility_info='Full elevator access to main prayer hall, ramps at entryway.',
            is_hidden_gem=False,
            source_attribution='ISKCON Cultural Board',
            last_verified_at=datetime.utcnow(),
            crowd_status='Normal',
            crowd_updated_at=datetime.utcnow() - timedelta(hours=1)
        )

        db.session.add_all([d_surajkund, d_nahar_singh, d_badkhal, d_asola, d_iskcon_fbd])
        db.session.flush()

        # Stories for Faridabad
        s_surajkund = Story(
            destination_id=d_surajkund.id,
            title='The Royal Sun Basin of the Tomar Kings',
            content='Surajkund, meaning the "Lake of the Sun", is an amphitheatre-shaped embankment built with dressed quartzite stone. Built in the 10th century CE by King Suraj Pal, its stepped terraced walls mirror the solar rays. Standing on the grand stone steps, one can envision royal priests chanting Vedic hymns at daybreak.',
            audio_text='Welcome to Surajkund. Look around at the sweeping semi-circular stepped reservoir. Built more than a thousand years ago by the Tomar Rajput ruler Suraj Pal, this massive amphitheatre was dedicated to Surya, the Hindu Sun God. The stone steps were aligned specifically to catch the morning sunrise over the Aravalli hills.',
            audio_duration_seconds=45,
            fun_facts='Surajkund was built long before the city of Delhi was established as an imperial capital!'
        )

        s_nahar = Story(
            destination_id=d_nahar_singh.id,
            title='The Courageous Fort of the 1857 Patriot King',
            content='Raja Nahar Singh was a courageous 32-year-old warrior king who defended Delhi’s southern frontier during the 1857 War of Independence. His palace features intricate Rajasthani jaali work, arched durbar halls, and tranquil water fountains that preserved royal elegance amidst wartime defiance.',
            audio_text='You are standing before Raja Nahar Singh Palace in Ballabhgarh. Here lived one of the most heroic figures of India’s 1857 Uprising. Notice the elegant sandstone arches and delicate latticed balconies. When British forces surrounded Delhi, King Nahar Singh guarded the southern border and refused all British demands to surrender.',
            audio_duration_seconds=50,
            fun_facts='The palace was designed with underground ventilation channels that kept the royal durbar cool without electricity!'
        )

        db.session.add_all([s_surajkund, s_nahar])

        # Seeding Other Cities (Agra, Shimla, Jaipur, Varanasi)
        print("Seeding Agra, Shimla, Jaipur, Varanasi Destinations...")
        d_taj = Destination(
            city_id=c_agra.id,
            name='Taj Mahal & Yamuna Riverfront',
            category='monument',
            description='World-renowned ivory-white marble mausoleum on the south bank of the Yamuna river, an architectural marvel of Mughal symmetry.',
            latitude=27.1751,
            longitude=78.0421,
            image_url='https://images.unsplash.com/photo-1564507592333-c60657eea523?auto=format&fit=crop&w=1000&q=80',
            historical_significance='Commissioned in 1631 by Mughal Emperor Shah Jahan to house the tomb of his favourite wife, Mumtaz Mahal.',
            local_stories='Optical illusion: the monument appears to grow larger as you walk backwards through the main gateway arch.',
            opening_hours='06:00 AM - 06:30 PM (Closed Fridays)',
            accessibility_info='Battery operated golf carts and ramps for wheelchair access.',
            is_hidden_gem=False,
            crowd_status='Overcrowded',
            crowd_explanation='Peak weekend international tourist influx. Security queue 55 mins.'
        )

        d_mehtab = Destination(
            city_id=c_agra.id,
            name='Mehtab Bagh (Moonlight Garden)',
            category='heritage',
            description='Charbagh garden complex situated perfectly across the Yamuna river, offering magnificent uncrowded views of the Taj Mahal.',
            latitude=27.1800,
            longitude=78.0425,
            image_url='https://images.unsplash.com/photo-1585135497273-1a86b09fe70e?auto=format&fit=crop&w=1000&q=80',
            historical_significance='Built by Emperor Babur in 1530 as a moonlight pleasure garden to view the river.',
            local_stories='Mughal accounts mention pool waters designed to reflect the white dome by moonlight.',
            opening_hours='06:00 AM - 06:00 PM',
            accessibility_info='Level paved stone pathways throughout the garden.',
            is_hidden_gem=True,
            crowd_status='Normal',
            crowd_explanation='Quiet green spaces, zero waiting lines.'
        )

        d_ridge = Destination(
            city_id=c_shimla.id,
            name='The Ridge & Christ Church',
            category='heritage',
            description='Expansive open cultural square along the crest of Shimla offering panoramic views of the Pir Panjal mountain ranges.',
            latitude=31.1044,
            longitude=77.1747,
            image_url='https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?auto=format&fit=crop&w=1000&q=80',
            historical_significance='Built in 1857, Christ Church is North India’s second oldest church with neo-Gothic stained glass.',
            local_stories='Church bells cast in England could once be heard echoing across distant apple valleys.',
            opening_hours='08:00 AM - 06:00 PM',
            accessibility_info='Pedestrian mall is completely flat and paved.',
            is_hidden_gem=False,
            crowd_status='Moderate'
        )

        d_potters_hill = Destination(
            city_id=c_shimla.id,
            name='Potters Hill Cedar Eco Forest',
            category='nature',
            description='Hidden dense Himalayan cedar reserve where potters once gathered red clay, now featuring suspension bridges and peaceful pine trails.',
            latitude=31.1215,
            longitude=77.1292,
            image_url='https://images.unsplash.com/photo-1473448912268-2022ce9509d8?auto=format&fit=crop&w=1000&q=80',
            historical_significance='Preserved ancient forest reserve supporting endangered Western Tragopan pheasants.',
            local_stories='Forest whispers among old deodar pines tell of wandering Sufi hermits.',
            opening_hours='08:00 AM - 05:00 PM',
            accessibility_info='Forest trail requires trekking shoes.',
            is_hidden_gem=True,
            crowd_status='Normal'
        )

        d_hawa_mahal = Destination(
            city_id=c_jaipur.id,
            name='Hawa Mahal (Palace of Winds)',
            category='heritage',
            description='Iconic five-storey pink and red sandstone palace with 953 honeycombed jharokha windows allowing breeze circulation.',
            latitude=26.9239,
            longitude=75.8267,
            image_url='https://images.unsplash.com/photo-1599661046289-e31897846e41?auto=format&fit=crop&w=1000&q=80',
            historical_significance='Built in 1799 by Maharaja Sawai Pratap Singh so royal women could observe street festivities unseen.',
            local_stories='The structure has no solid foundation; its slight incline keeps it structurally stable.',
            opening_hours='09:00 AM - 05:00 PM',
            accessibility_info='Narrow stairways inside; street viewing terrace is wheelchair accessible.',
            is_hidden_gem=False,
            crowd_status='Crowded'
        )

        d_panna_meena = Destination(
            city_id=c_jaipur.id,
            name='Panna Meena ka Kund (Hidden Stepwell)',
            category='heritage',
            description='An astonishing 16th-century geometric stepwell with interlocking criss-cross stone stairs in Amer.',
            latitude=26.9856,
            longitude=75.8569,
            image_url='https://images.unsplash.com/photo-1582510003544-4d00b7f74220?auto=format&fit=crop&w=1000&q=80',
            historical_significance='Community water harvesting sanctuary engineered by Meena rulers before the Kachwaha dynasty.',
            local_stories='Locals say no person can use the exact same stairs to climb up as they did to descend!',
            opening_hours='07:00 AM - 06:00 PM',
            accessibility_info='Viewing deck accessible from road.',
            is_hidden_gem=True,
            crowd_status='Normal'
        )

        d_dashashwamedh = Destination(
            city_id=c_varanasi.id,
            name='Dashashwamedh Ghat & Ganga Aarti',
            category='spiritual',
            description='The premier sacred river ghat of Varanasi where priests perform choreography with brass lamps against the sacred Ganga.',
            latitude=25.3076,
            longitude=83.0104,
            image_url='https://images.unsplash.com/photo-1561361513-2d000a50f0dc?auto=format&fit=crop&w=1000&q=80',
            historical_significance='According to myth, Lord Brahma performed the ten-horse sacrifice (Dasa-Ashwamedha) here.',
            local_stories='Thousands of clay diyas float downriver every sunset, turning the river into a galaxy of light.',
            opening_hours='Open 24 hours (Aarti at 06:45 PM)',
            accessibility_info='Stone steps descending to river; boat boarding assistance available.',
            is_hidden_gem=False,
            crowd_status='Overcrowded',
            crowd_explanation='Evening Ganga Aarti crowd gathering; heavy congestion on approach lanes.'
        )

        d_sarnath = Destination(
            city_id=c_varanasi.id,
            name='Sarnath Deer Park & Dhamek Stupa',
            category='spiritual',
            description='Tranquil monastic archaeological deer park where Gautama Buddha taught his first sermon on the Four Noble Truths.',
            latitude=25.3811,
            longitude=83.0214,
            image_url='https://images.unsplash.com/photo-1590766940554-634a7ed41450?auto=format&fit=crop&w=1000&q=80',
            historical_significance='Historic site of Buddha’s Dharmachakra Pravartana (Turning of the Wheel of Law) in 528 BCE.',
            local_stories='Emperor Ashoka erected his famous four-lion capital pillar here, which now serves as India’s National Emblem.',
            opening_hours='06:00 AM - 05:30 PM',
            accessibility_info='Spacious paved pathways through gardens, full accessibility.',
            is_hidden_gem=True,
            crowd_status='Normal',
            crowd_explanation='Peaceful meditative atmosphere.'
        )

        db.session.add_all([
            d_taj, d_mehtab, d_ridge, d_potters_hill,
            d_hawa_mahal, d_panna_meena, d_dashashwamedh, d_sarnath
        ])
        db.session.flush()

        # Stories for additional cities
        s_taj = Story(
            destination_id=d_taj.id,
            title='Symphony in White Marble',
            content='Crafted from white Makrana marble brought across 300 kilometres by thousands of elephants, the Taj Mahal is an ode to eternal love. Pietra dura inlays of lapis lazuli, turquoise, and carnelian blossom across the cenotaphs.',
            audio_text='You are witnessing the Taj Mahal. Built by Emperor Shah Jahan in memory of Mumtaz Mahal, notice the optical perfection. The four minarets lean outward by two degrees so that during an earthquake they would fall away from the sacred dome.',
            audio_duration_seconds=40
        )
        s_sarnath = Story(
            destination_id=d_sarnath.id,
            title='The First Turning of the Wheel of Wisdom',
            content='Under quiet bodhi leaves in this deer park, Siddhartha Gautama delivered his very first discourse to five disciples after attaining enlightenment. The ancient Dhamek Stupa stands 43 metres high.',
            audio_text='Welcome to peaceful Sarnath. In this very deer park twenty-five hundred years ago, the Buddha first taught the Middle Path. Stand before the Dhamek Stupa and observe the intricate Gupta-period floral carvings.',
            audio_duration_seconds=45
        )
        db.session.add_all([s_taj, s_sarnath])

        print("Seeding Activities & Cuisine...")
        # Activities in Faridabad
        act_fbd_pottery = Activity(
            city_id=c_fbd.id,
            destination_id=d_surajkund.id,
            name='Surajkund Traditional Terracotta & Craft Workshop',
            category='workshop',
            description='Master artisans teach hands-on pottery shaping and block printing using ancient Haryana terracotta clays.',
            price_range='₹250 - ₹500',
            typical_duration='1.5 hours',
            recommended_time='Morning (10:00 AM)',
            safety_precautions='Non-toxic natural clay and eco-friendly vegetable dyes provided.',
            price_source='Sample data; verify with the local operator',
            image_url='https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?auto=format&fit=crop&w=800&q=80'
        )
        act_fbd_walk = Activity(
            city_id=c_fbd.id,
            destination_id=d_nahar_singh.id,
            name='Ballabhgarh Royal Heritage Walking Tour',
            category='heritage_walk',
            description='Guided storytelling walk through historical gateways, 1857 rebel battlegrounds, and royal durbar chambers.',
            price_range='₹350 per person',
            typical_duration='2 hours',
            recommended_time='Late Afternoon (04:00 PM)',
            safety_precautions='Comfortable walking shoes recommended; bottled water provided.',
            price_source='Sample data; verify with the local operator',
            image_url='https://images.unsplash.com/photo-1590050752117-238cb0fb12b1?auto=format&fit=crop&w=800&q=80'
        )
        act_fbd_lake = Activity(
            city_id=c_fbd.id,
            destination_id=d_asola.id,
            name='Aravalli Ridge Eco Trail & Bird Watching',
            category='trek',
            description='Guided sunrise nature expedition spotting peacocks, painted storks, and desert monitors along turquoise quarry lakes.',
            price_range='Free (Forest entry pass ₹50)',
            typical_duration='3 hours',
            recommended_time='Sunrise (06:30 AM)',
            safety_precautions='Stay on marked trails; do not attempt swimming in deep quarry waters.',
            price_source='Sample data; verify with the local operator',
            image_url='https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=800&q=80'
        )
        db.session.add_all([act_fbd_pottery, act_fbd_walk, act_fbd_lake])

        # Cuisines in Faridabad
        c_bajra = CuisineItem(
            city_id=c_fbd.id,
            name='Haryanvi Bajra Khichdi with Fresh White Butter',
            description='Wholesome slow-cooked pearl millet and yellow moong dal topped with organic churned makkhan (white butter) and jaggery.',
            cultural_background='Traditional winter staple of rural Haryana farmers, providing rich sustained stamina in cold farming months.',
            dietary_tags='vegetarian,gluten-free,wholesome',
            allergen_info='Contains dairy (butter/ghee). Vegan option available without butter.',
            price_range='₹120 - ₹220',
            famous_spots='Haveli Faridabad, NH-19 Dhaba Belt',
            user_rating=4.9,
            image_url='https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=800&q=80'
        )
        c_kadhi = CuisineItem(
            city_id=c_fbd.id,
            name='Haryanvi Kadhi Pakora with Jeera Rice',
            description='Tangy slow-simmered buttermilk yogurt gravy infused with fenugreek seeds, fried onion fritters, and whole red chillies.',
            cultural_background='A celebratory village wedding dish cooked in copper degs over wood fires.',
            dietary_tags='vegetarian,comfort-food',
            allergen_info='Contains yogurt (dairy) and gram flour.',
            price_range='₹100 - ₹180',
            famous_spots='Raja Chowk Ballabhgarh, Sector 15 Market',
            user_rating=4.8,
            image_url='https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=800&q=80'
        )
        c_jalebi = CuisineItem(
            city_id=c_fbd.id,
            name='Gohana Desi Ghee Giant Jalebi',
            description='Famous oversized crispy spirals fried in pure desi ghee and soaked in saffron cardamom sugar nectar.',
            cultural_background='A state icon of Haryana culinary joy, freshly served warm in morning and dusk.',
            dietary_tags='vegetarian,street-food,dessert',
            allergen_info='Contains wheat gluten and milk solids.',
            price_range='₹80 - ₹150',
            famous_spots='Old Faridabad Station Bazaar, Neelam Flyover',
            user_rating=4.9,
            image_url='https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=800&q=80'
        )
        db.session.add_all([c_bajra, c_kadhi, c_jalebi])

        # Cuisines for other cities
        c_petha = CuisineItem(
            city_id=c_agra.id,
            name='Agra Angoori Petha',
            description='Translucent candied ash gourd sweet flavoured with saffron, rosewater, and pistachio.',
            cultural_background='Originated in royal Mughal kitchens to fuel workers carving the Taj Mahal.',
            dietary_tags='vegetarian,vegan,gluten-free',
            allergen_info='Gluten free; nut garnishes optional.',
            price_range='₹70 - ₹180',
            famous_spots='Panchi Petha, Sadar Bazaar Agra',
            user_rating=4.8,
            image_url='https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?auto=format&fit=crop&w=800&q=80'
        )
        c_siddu = CuisineItem(
            city_id=c_shimla.id,
            name='Himachali Siddu with Walnut Chutney',
            description='Steamed wheat flour bun stuffed with poppy seeds, spiced lentils, and walnuts, served hot with pure ghee.',
            cultural_background='Highland delicacy cooked in cold weather to retain warmth and nutrition.',
            dietary_tags='vegetarian,mountain-heritage',
            allergen_info='Contains wheat gluten and tree nuts.',
            price_range='₹90 - ₹160',
            famous_spots='Mall Road Traditional Cafes, Lakkar Bazaar',
            user_rating=4.9,
            image_url='https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?auto=format&fit=crop&w=800&q=80'
        )
        c_dalbaati = CuisineItem(
            city_id=c_jaipur.id,
            name='Rajasthani Dal Baati Churma',
            description='Crisp baked wheat balls soaked in ghee, served with five-lentil curry and crushed sweet churma.',
            cultural_background='Royal martial dish of Rajput warriors, engineered to survive long desert campaigns.',
            dietary_tags='vegetarian,royal-heritage',
            allergen_info='Contains wheat gluten and dairy.',
            price_range='₹180 - ₹350',
            famous_spots='Laxmi Mishthan Bhandar (LMB), Chokhi Dhani',
            user_rating=4.9,
            image_url='https://images.unsplash.com/photo-1610057099443-fde8c4d50f91?auto=format&fit=crop&w=800&q=80'
        )
        c_paan = CuisineItem(
            city_id=c_varanasi.id,
            name='Banarasi Meetha Maghai Paan',
            description='Betel leaf parcel filled with gulkand (rose petal preserve), sweet fennel, menthol, and exotic silver foil.',
            cultural_background='Elevated to high art form in Kashi, celebrated in classical folklore and poetry.',
            dietary_tags='vegetarian,vegan,digestive',
            allergen_info='Contains areca nut and sweet syrup.',
            price_range='₹30 - ₹80',
            famous_spots='Keshav Paan Bhandar, Dashashwamedh Ghat',
            user_rating=4.9,
            image_url='https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=800&q=80'
        )
        db.session.add_all([c_petha, c_siddu, c_dalbaati, c_paan])

        print("Seeding Transparent Transport Options...")
        # Transport for Faridabad
        t_metro = TransportOption(
            city_id=c_fbd.id,
            mode='metro',
            name_or_route='Delhi Metro Violet Line (Kashmere Gate ⇄ Raja Nahar Singh Ballabhgarh)',
            operating_hours='05:45 AM - 11:00 PM',
            fare_estimate='₹20 - ₹60 (Token / Smart Card)',
            frequency='Every 5 to 8 minutes',
            sample_timings='Peak: 08:00-11:00 & 17:00-20:30 (5 min intervals); Off-peak: 8 min intervals',
            source_type='sample',
            details='Fully air-conditioned rapid transit with direct elevated stations across Faridabad (Neelam Chowk, Bata Chowk, Escorts Mujesar, Ballabhgarh). Step-free elevator access and dedicated women coaches.',
            image_url='https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80'
        )
        t_bus = TransportOption(
            city_id=c_fbd.id,
            mode='bus',
            name_or_route='Haryana City Bus Services (Faridabad Circular Route 901)',
            operating_hours='06:30 AM - 09:30 PM',
            fare_estimate='₹10 - ₹25 cash / contactless pass',
            frequency='Every 15-20 minutes',
            sample_timings='Connects Badkhal Flyover, NIT Bus Stand, Old Faridabad, and Surajkund Gate',
            source_type='sample',
            details='Low-floor CNG and electric city transit buses. Affordable local commuting linking metro hubs with residential sectors.',
            image_url='https://images.unsplash.com/photo-1570125909232-eb263c188f7e?auto=format&fit=crop&w=800&q=80'
        )
        t_auto = TransportOption(
            city_id=c_fbd.id,
            mode='auto_rickshaw',
            name_or_route='Prepaid / Metered CNG Auto & e-Rickshaws',
            operating_hours='24 Hours (Available near Metro gates & railway stations)',
            fare_estimate='Base ₹30 + ₹12/km; e-rickshaw shared ₹10-20',
            frequency='Immediate on-demand hailing',
            sample_timings='Available outside all metro stations',
            source_type='sample',
            details='Ideal for last-mile connectivity from metro stations into historical monuments and local food lanes.',
            image_url='https://images.unsplash.com/photo-1588668214407-6ea9a6d8c272?auto=format&fit=crop&w=800&q=80'
        )
        db.session.add_all([t_metro, t_bus, t_auto])

        
        # Populate extended user-specified destinations, activities, and cuisine
        from seed_user_content import populate_user_content
        populate_user_content(app=app)

        Destination.query.update({
            Destination.source_attribution: 'Unverified sample data',
            Destination.last_verified_at: None,
            Destination.crowd_status: 'Normal',
            Destination.crowd_updated_at: datetime.utcnow(),
            Destination.crowd_explanation: None,
            Destination.crowd_expires_at: None
        }, synchronize_session=False)
        Activity.query.update({
            Activity.price_source: 'Sample data; verify locally',
            Activity.last_verified_at: None
        }, synchronize_session=False)
        CuisineItem.query.update({
            CuisineItem.verified_status: 'sample',
            CuisineItem.user_rating: None,
            CuisineItem.allergen_info: 'Not verified; ask the vendor'
        }, synchronize_session=False)
        TransportOption.query.update({
            TransportOption.source_type: 'sample'
        }, synchronize_session=False)

        db.session.commit()
        print("Database seeded successfully with rich travel data!")
        return True

if __name__ == '__main__':
    seed()
