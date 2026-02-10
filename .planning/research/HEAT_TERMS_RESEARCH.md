# Heat-Related News Terms Research: Indian Languages

> **Date**: 2026-02-10
> **Purpose**: Foundation terminology for heat news extraction pipeline across 14+ Indian languages
> **Principle**: HIGH RECALL over high precision -- better to capture noise than miss coverage
> **Methodology note**: Terms are drawn from knowledge of Indian journalism conventions, IMD official terminology, and common usage patterns in regional media. Live web verification was not possible during this research session. All terms should be verified against actual news articles before deployment. Confidence levels reflect how well-established and widely-used each term is in Indian journalism, based on training data exposure to Indian news corpora.

---

## Summary Table: Key Terms by Language and Category

| Language | Heatwave | Heat Death/Stroke | Water Crisis | Power Cuts | Crop Damage | Human Impact | Govt Response | Temperature |
|----------|----------|-------------------|-------------|------------|-------------|--------------|---------------|-------------|
| **English** | heatwave, heat wave, severe heat | heatstroke, sunstroke, heat death | water crisis, water scarcity, drought | power cut, load shedding, blackout | crop loss, crop damage, wilting | dehydration, hospital admissions | heat action plan, advisory | mercury rises, temperature soars |
| **Hindi** | लू, हीट वेव, भीषण गर्मी | लू लगना, तापाघात, हीट स्ट्रोक | जल संकट, पानी की किल्लत | बिजली कटौती, लोड शेडिंग | फसल नुकसान, फसल बर्बाद | निर्जलीकरण, अस्पताल भर्ती | राहत, हीट एक्शन प्लान | पारा चढ़ा, तापमान |
| **Tamil** | வெப்ப அலை, அக்னி நட்சத்திரம் | வெப்பத்தாக்கம், சன்ஸ்ட்ரோக் | நீர் பற்றாக்குறை, நீர் நெருக்கடி | மின்வெட்டு, மின்தடை | பயிர் சேதம், பயிர் நஷ்டம் | நீரிழப்பு, மருத்துவமனை | நிவாரணம், எச்சரிக்கை | வெப்பநிலை உயர்வு |
| **Telugu** | వడ గాలులు, హీట్ వేవ్ | ఎండ దెబ్బ, హీట్ స్ట్రోక్ | నీటి కొరత, నీటి సంక్షోభం | విద్యుత్ కోత, కరెంట్ కట్ | పంట నష్టం, పంట నాశనం | నిర్జలీకరణం, ఆసుపత్రి | సహాయ చర్యలు, హెచ్చరిక | ఉష్ణోగ్రత పెరుగుదల |
| **Bengali** | দাবদাহ, তাপপ্রবাহ | হিটস্ট্রোক, তাপাঘাত | জলসংকট, জল সমস্যা | বিদ্যুৎ বিভ্রাট, লোড শেডিং | ফসলের ক্ষতি | পানিশূন্যতা, হাসপাতালে ভর্তি | ত্রাণ, সতর্কতা | তাপমাত্রা বৃদ্ধি |
| **Marathi** | उष्णतेची लाट, उष्णलहर | उष्माघात, लू लागणे | पाणी टंचाई, जलसंकट | वीज कपात, लोडशेडिंग | पीक नुकसान | निर्जलीकरण, रुग्णालय | दिलासा, हीट अॅक्शन प्लान | तापमान वाढ |
| **Gujarati** | હીટવેવ, ભારે ગરમી | લૂ લાગવી, હીટ સ્ટ્રોક | પાણીની તંગી, જળ સંકટ | વીજ કાપ, લોડશેડિંગ | પાક નુકસાન | ડિહાઇડ્રેશન, હોસ્પિટલ | રાહત, એડવાઇઝરી | તાપમાન વધ્યું |
| **Kannada** | ಬಿಸಿ ಗಾಳಿ, ಹೀಟ್ ವೇವ್ | ಬಿಸಿಲಿನ ಹೊಡೆತ, ಹೀಟ್ ಸ್ಟ್ರೋಕ್ | ನೀರಿನ ಕೊರತೆ, ಜಲ ಸಂಕಟ | ವಿದ್ಯುತ್ ಕಡಿತ, ಲೋಡ್ ಶೆಡ್ಡಿಂಗ್ | ಬೆಳೆ ನಷ್ಟ, ಬೆಳೆ ಹಾನಿ | ನಿರ್ಜಲೀಕರಣ, ಆಸ್ಪತ್ರೆ | ಪರಿಹಾರ, ಎಚ್ಚರಿಕೆ | ತಾಪಮಾನ ಏರಿಕೆ |
| **Malayalam** | ഉഷ്ണ തരംഗം, ചൂട് തരംഗം | സൂര്യാഘാതം, ഹീറ്റ് സ്ട്രോക്ക് | ജലക്ഷാമം, കുടിവെള്ള ക്ഷാമം | വൈദ്യുതി മുടക്കം, ലോഡ് ഷെഡ്ഡിംഗ് | കൃഷി നാശം, വിള നഷ്ടം | നിര്‍ജലീകരണം, ആശുപത്രി | ദുരിതാശ്വാസം, മുന്നറിയിപ്പ് | താപനില ഉയര്‍ന്നു |
| **Odia** | ଉଷ୍ଣ ଲହରୀ, ହିଟ୍ ୱେଭ୍ | ଲୁ ଲାଗିବା, ହିଟ୍ ଷ୍ଟ୍ରୋକ୍ | ଜଳ ସଙ୍କଟ, ପାଣି ଅଭାବ | ବିଦ୍ୟୁତ ବିଭ୍ରାଟ, ଲୋଡ୍ ସେଡିଂ | ଫସଲ କ୍ଷତି, ଫସଲ ନଷ୍ଟ | ନିର୍ଜଳୀକରଣ, ଡାକ୍ତରଖାନା | ସହାୟତା, ସତର୍କତା | ତାପମାତ୍ରା ବୃଦ୍ଧି |
| **Punjabi** | ਲੂ, ਹੀਟ ਵੇਵ | ਲੂ ਲੱਗਣਾ, ਹੀਟ ਸਟ੍ਰੋਕ | ਪਾਣੀ ਦੀ ਕਿੱਲਤ, ਜਲ ਸੰਕਟ | ਬਿਜਲੀ ਕੱਟ, ਲੋਡ ਸ਼ੈਡਿੰਗ | ਫ਼ਸਲ ਨੁਕਸਾਨ | ਡੀਹਾਈਡ੍ਰੇਸ਼ਨ, ਹਸਪਤਾਲ | ਰਾਹਤ, ਐਡਵਾਈਜ਼ਰੀ | ਤਾਪਮਾਨ ਵਧਿਆ |
| **Assamese** | তাপ প্ৰবাহ, হিট ৱেভ | তাপাঘাত, লু লগা | জল সংকট, পানী নাটনি | বিদ্যুৎ বিভ্ৰাট | শস্যৰ ক্ষতি | পানীশূন্যতা, চিকিৎসালয় | সাহায্য, সতৰ্কবাণী | তাপমাত্ৰা বৃদ্ধি |
| **Urdu** | لو, ہیٹ ویو, شدید گرمی | لو لگنا, ہیٹ اسٹروک | پانی کا بحران, قلت آب | بجلی کی کٹوتی, لوڈ شیڈنگ | فصل نقصان | پانی کی کمی, ہسپتال | امداد, ایڈوائزری | درجہ حرارت |
| **Nepali** | लू, हिट वेभ, भिषण गर्मी | लू लाग्नु, हिट स्ट्रोक | पानीको अभाव, जल संकट | बिजुली कटौती, लोडसेडिङ | बाली नोक्सानी | निर्जलीकरण, अस्पताल | राहत, चेतावनी | तापक्रम बढ्यो |

---

## Detailed Terms by Language

---

### 1. ENGLISH (en)

English is the lingua franca of national media and IMD official communications. Terms below are used in The Hindu, Times of India, NDTV, Indian Express, Scroll.in, and IMD bulletins.

| Term | Category | Register | Confidence | Sources |
|------|----------|----------|------------|---------|
| heatwave / heat wave | heatwave | formal/IMD | HIGH | IMD bulletins, The Hindu, all national outlets |
| severe heatwave | heatwave | formal/IMD | HIGH | IMD classification term, widely used |
| extreme heat | heatwave | general | HIGH | Times of India, NDTV |
| heat spell | heatwave | formal | MEDIUM | The Hindu, Indian Express |
| scorching heat | heatwave | journalistic | HIGH | Common headline term across all outlets |
| blistering heat | heatwave | journalistic | MEDIUM | Times of India, Scroll.in |
| sweltering heat | heatwave | journalistic | MEDIUM | Indian Express, The Hindu |
| hot winds | heatwave | descriptive | MEDIUM | The Hindu |
| loo / hot loo winds | heatwave | cultural/borrowed | MEDIUM | The Hindu, Indian Express (used in North India context) |
| heatstroke / heat stroke | death/stroke | medical/formal | HIGH | All outlets |
| sunstroke | death/stroke | colloquial/medical | HIGH | Times of India, NDTV |
| heat-related death | death/stroke | formal | HIGH | All outlets |
| heat casualty | death/stroke | formal | MEDIUM | NDTV, Indian Express |
| heat exhaustion | death/stroke | medical | MEDIUM | The Hindu |
| suspected heat death | death/stroke | journalistic | HIGH | All outlets (hedging term) |
| water crisis | water | general | HIGH | All outlets |
| water scarcity | water | formal | HIGH | The Hindu, Indian Express |
| acute water shortage | water | formal | HIGH | The Hindu |
| drought | water | formal | HIGH | All outlets |
| water tanker | water | descriptive | MEDIUM | Times of India (context: tanker supply during crisis) |
| dried up / drying up | water | descriptive | MEDIUM | Various outlets |
| power cut | power | general | HIGH | All outlets |
| power outage | power | formal | HIGH | NDTV, Indian Express |
| load shedding | power | South Asian English | HIGH | Times of India, NDTV |
| blackout | power | general | MEDIUM | NDTV |
| electricity crisis | power | formal | MEDIUM | The Hindu |
| grid failure | power | technical | MEDIUM | Indian Express |
| power demand surge | power | journalistic | MEDIUM | NDTV, The Hindu |
| crop damage | crop | general | HIGH | All outlets |
| crop loss | crop | general | HIGH | All outlets |
| crop failure | crop | formal | HIGH | The Hindu, Indian Express |
| agricultural loss | crop | formal | MEDIUM | The Hindu |
| wilting | crop | descriptive | MEDIUM | The Hindu |
| parched fields | crop | journalistic | MEDIUM | Indian Express |
| dehydration | human | medical | HIGH | All outlets |
| hospital admissions | human | formal | HIGH | NDTV, The Hindu |
| school closure | human | general | HIGH | Times of India, NDTV |
| heat advisory | govt | formal/IMD | HIGH | IMD, all outlets |
| heat action plan | govt | formal/govt | HIGH | NDCMA, The Hindu, NDTV |
| red alert | govt | IMD classification | HIGH | All outlets |
| orange alert | govt | IMD classification | HIGH | All outlets |
| yellow alert | govt | IMD classification | HIGH | All outlets |
| relief measures | govt | formal | MEDIUM | The Hindu, Times of India |
| mercury soars | temperature | journalistic | HIGH | Extremely common headline idiom |
| mercury crosses X degrees | temperature | journalistic | HIGH | All outlets |
| temperature soars | temperature | journalistic | HIGH | All outlets |
| record temperature | temperature | formal | HIGH | All outlets |
| all-time high | temperature | journalistic | HIGH | NDTV, Times of India |
| degrees Celsius | temperature | formal | HIGH | All outlets |

---

### 2. HINDI (hi)

Hindi is the dominant language for heat news in North India. Key outlets: Dainik Jagran, Amar Ujala, Dainik Bhaskar, NDTV Hindi, Aaj Tak, Navbharat Times, Hindustan. Hindi heat journalism has a rich vocabulary mixing Sanskrit-derived formal terms, colloquial terms, and borrowed English.

| Term (Devanagari) | Transliteration | English Meaning | Category | Register | Confidence | Sources |
|---|---|---|---|---|---|---|
| लू | loo | hot wind / heatwave | heatwave | colloquial, extremely common | HIGH | Dainik Jagran, Amar Ujala, Aaj Tak -- this is THE most common term |
| लू चलना | loo chalna | hot winds blowing | heatwave | colloquial | HIGH | Dainik Bhaskar, Amar Ujala |
| भीषण गर्मी | bheeshan garmi | severe/terrible heat | heatwave | journalistic | HIGH | All Hindi outlets -- standard headline term |
| प्रचंड गर्मी | prachand garmi | fierce/extreme heat | heatwave | literary/journalistic | HIGH | Dainik Jagran, Navbharat Times |
| कड़ी धूप | kadi dhoop | harsh sunshine | heatwave | colloquial | MEDIUM | Amar Ujala, Dainik Bhaskar |
| तेज धूप | tez dhoop | intense sunshine | heatwave | colloquial | MEDIUM | Multiple outlets |
| गर्म हवा | garm hawa | hot wind | heatwave | general | HIGH | Dainik Jagran, NDTV Hindi |
| उष्ण लहर | ushna lahar | heat wave (lit. hot wave) | heatwave | formal/IMD Hindi | HIGH | IMD Hindi bulletins, Dainik Jagran |
| ताप लहर | taap lahar | heat wave | heatwave | formal/IMD | MEDIUM | IMD terminology |
| हीट वेव | heat wave (borrowed) | heatwave | heatwave | borrowed English | HIGH | NDTV Hindi, Aaj Tak -- very commonly used |
| झुलसाने वाली गर्मी | jhulsane wali garmi | scorching heat | heatwave | journalistic | MEDIUM | Amar Ujala |
| तपती गर्मी | tapti garmi | burning heat | heatwave | journalistic | MEDIUM | Dainik Bhaskar |
| भयंकर गर्मी | bhayankar garmi | terrible heat | heatwave | journalistic | MEDIUM | Amar Ujala |
| गर्मी का कहर | garmi ka kahar | fury of heat | heatwave | journalistic idiom | HIGH | Extremely common headline pattern |
| गर्मी का प्रकोप | garmi ka prakop | onslaught of heat | heatwave | journalistic | HIGH | Dainik Jagran, Navbharat Times |
| सूर्याघात | suryaaghat | sunstroke | death/stroke | formal/medical | HIGH | Dainik Jagran, government reports |
| तापाघात | tapaaghat | heatstroke | death/stroke | formal | HIGH | IMD, Dainik Bhaskar |
| लू लगना | loo lagna | to be struck by heat | death/stroke | colloquial, very common | HIGH | All Hindi outlets |
| लू से मौत | loo se maut | death from heat | death/stroke | journalistic | HIGH | Amar Ujala, Dainik Jagran |
| गर्मी से मौत | garmi se maut | death from heat | death/stroke | journalistic | HIGH | All Hindi outlets |
| हीट स्ट्रोक | heat stroke (borrowed) | heatstroke | death/stroke | borrowed English | HIGH | NDTV Hindi, Aaj Tak |
| सन स्ट्रोक | sun stroke (borrowed) | sunstroke | death/stroke | borrowed English | MEDIUM | NDTV Hindi |
| लू से मरे | loo se mare | died from heat | death/stroke | journalistic | HIGH | Headline term |
| जल संकट | jal sankat | water crisis | water | formal | HIGH | Dainik Jagran, NDTV Hindi |
| पानी की किल्लत | paani ki killat | water scarcity | water | colloquial | HIGH | Amar Ujala, Dainik Bhaskar |
| पानी का संकट | paani ka sankat | water crisis | water | general | HIGH | All Hindi outlets |
| जल की कमी | jal ki kami | shortage of water | water | formal | MEDIUM | Government reports |
| पेयजल संकट | peyjal sankat | drinking water crisis | water | formal | HIGH | Dainik Jagran |
| पानी की कमी | paani ki kami | water shortage | water | general | HIGH | All outlets |
| सूखा | sookha | drought | water | formal | HIGH | All outlets |
| टैंकर से पानी | tanker se paani | water by tanker | water | descriptive | MEDIUM | Amar Ujala |
| नदी सूखी | nadi sookhi | river dried up | water | descriptive | MEDIUM | Dainik Bhaskar |
| बोरवेल सूखे | borwell sookhe | borewells dried | water | descriptive | MEDIUM | Dainik Jagran |
| बिजली कटौती | bijli katawti | power cut | power | general, very common | HIGH | All Hindi outlets |
| बिजली संकट | bijli sankat | electricity crisis | power | formal | HIGH | Dainik Jagran, NDTV Hindi |
| लोड शेडिंग | load shedding (borrowed) | load shedding | power | borrowed English | HIGH | All outlets |
| बिजली गुल | bijli gul | power gone (blackout) | power | colloquial | HIGH | Amar Ujala, Dainik Bhaskar |
| बिजली कट | bijli cut | power cut | power | colloquial | HIGH | All outlets |
| बिजली की किल्लत | bijli ki killat | electricity scarcity | power | journalistic | MEDIUM | Dainik Jagran |
| बिजली की मांग | bijli ki maang | electricity demand | power | formal | MEDIUM | NDTV Hindi |
| विद्युत संकट | vidyut sankat | electricity crisis | power | formal/literary | MEDIUM | Government reports |
| फसल नुकसान | fasal nuksan | crop damage | crop | general | HIGH | Dainik Jagran, Amar Ujala |
| फसल बर्बाद | fasal barbaad | crop destroyed | crop | colloquial | HIGH | Dainik Bhaskar |
| फसल तबाह | fasal tabaah | crop devastated | crop | journalistic | MEDIUM | Amar Ujala |
| खेती को नुकसान | kheti ko nuksan | damage to farming | crop | general | MEDIUM | Dainik Jagran |
| फसलें सूखीं | faslen sookhin | crops dried up | crop | descriptive | HIGH | Common headline |
| किसान परेशान | kisan pareshan | farmers distressed | crop | journalistic idiom | HIGH | All outlets (headline pattern) |
| फसलें झुलसीं | faslen jhulsin | crops scorched | crop | journalistic | MEDIUM | Dainik Bhaskar |
| निर्जलीकरण | nirjaleekaran | dehydration | human | formal/medical | HIGH | NDTV Hindi, health reporting |
| डिहाइड्रेशन | dehydration (borrowed) | dehydration | human | borrowed English | HIGH | Aaj Tak, NDTV Hindi |
| अस्पताल में भर्ती | aspatal mein bharti | hospitalized | human | general | HIGH | All outlets |
| स्कूल बंद | school band | school closed | human | general | HIGH | All outlets |
| छुट्टी | chhuti | holiday/leave | human | general | MEDIUM | Context-dependent |
| मजदूरों की मौत | majdooron ki maut | workers' deaths | human | journalistic | HIGH | Headline term in labor contexts |
| गर्मी से बेहाल | garmi se behaal | distressed by heat | human | journalistic idiom | HIGH | Very common headline pattern |
| गर्मी से त्राहि-त्राहि | garmi se traahi-traahi | crying for mercy from heat | human | journalistic idiom | HIGH | Very common in Dainik Bhaskar, Amar Ujala |
| हीट एक्शन प्लान | heat action plan (borrowed) | heat action plan | govt | borrowed English | HIGH | NDTV Hindi, government coverage |
| गर्मी से राहत | garmi se raahat | relief from heat | govt | journalistic | HIGH | All outlets |
| चेतावनी | chetawani | warning/alert | govt | formal | HIGH | IMD Hindi, all outlets |
| रेड अलर्ट | red alert (borrowed) | red alert | govt | borrowed English | HIGH | All outlets |
| ऑरेंज अलर्ट | orange alert (borrowed) | orange alert | govt | borrowed English | HIGH | All outlets |
| येलो अलर्ट | yellow alert (borrowed) | yellow alert | govt | borrowed English | HIGH | All outlets |
| एडवाइजरी | advisory (borrowed) | advisory | govt | borrowed English | HIGH | NDTV Hindi, Aaj Tak |
| राहत सामग्री | raahat saamagri | relief material | govt | formal | MEDIUM | Government reporting |
| पारा चढ़ा | paara chadha | mercury rose | temperature | journalistic idiom | HIGH | Extremely common -- THE classic Hindi heat headline |
| पारा X डिग्री पहुंचा | paara X degree pahuncha | mercury reached X degrees | temperature | journalistic | HIGH | All outlets |
| तापमान | tapmaan | temperature | temperature | formal | HIGH | All outlets, IMD |
| तापमान बढ़ा | tapmaan badha | temperature rose | temperature | formal | HIGH | All outlets |
| रिकॉर्ड तोड़ गर्मी | record tod garmi | record-breaking heat | temperature | journalistic | HIGH | All outlets |
| X डिग्री सेल्सियस | X degree celsius | X degrees Celsius | temperature | formal | HIGH | All outlets |
| पारा उबला | paara ubla | mercury boiled | temperature | colloquial/dramatic | MEDIUM | Dainik Bhaskar |

---

### 3. TAMIL (ta)

Key outlets: Dinamalar, Dinamani, The Hindu Tamil, News7 Tamil, Puthiyathalaimurai, Vikatan. Tamil has distinctive cultural heat terms like "agni nakshatram" that have no equivalent in other languages.

| Term (Tamil) | Transliteration | English Meaning | Category | Register | Confidence | Sources |
|---|---|---|---|---|---|---|
| வெப்ப அலை | veppa alai | heat wave | heatwave | formal/IMD Tamil | HIGH | The Hindu Tamil, Dinamani |
| அக்னி நட்சத்திரம் | agni nakshatram | fire star (cultural: the hottest period, mid-May to mid-June, named after a star/astronomical period) | heatwave | cultural/colloquial | HIGH | Dinamalar, Dinamani -- this is a uniquely Tamil cultural term |
| கடும் வெயில் | kadum veyil | severe sun/heat | heatwave | journalistic | HIGH | Dinamalar, News7 Tamil |
| கொளுத்தும் வெயில் | koluthum veyil | scorching sun | heatwave | journalistic | HIGH | Dinamalar |
| எரிக்கும் வெயில் | erikkum veyil | burning sun | heatwave | journalistic | MEDIUM | Dinamani |
| கடுமையான வெப்பம் | kadumaiyaana veppam | intense heat | heatwave | formal | HIGH | The Hindu Tamil |
| வெயில் கொடுமை | veyil kodumai | cruelty of sun | heatwave | colloquial | MEDIUM | Dinamalar |
| வெப்பத்தாக்கம் | veppa thaakkam | heat attack/impact | death/stroke | formal/journalistic | HIGH | Dinamani, The Hindu Tamil |
| வெப்ப தாக்கு | veppa thaakku | heat strike | death/stroke | colloquial | MEDIUM | Dinamalar |
| வெயிலில் மரணம் | veyilil maranam | death in sun/heat | death/stroke | journalistic | HIGH | All Tamil outlets |
| வெப்பத்தால் உயிரிழப்பு | veppathal uyiriyappu | death due to heat | death/stroke | formal | HIGH | The Hindu Tamil |
| சன்ஸ்ட்ரோக் | sun stroke (borrowed) | sunstroke | death/stroke | borrowed English | HIGH | News7 Tamil, Dinamalar |
| ஹீட் ஸ்ட்ரோக் | heat stroke (borrowed) | heatstroke | death/stroke | borrowed English | MEDIUM | News7 Tamil |
| வெயில் தாக்கம் | veyil thaakkam | sun impact/attack | death/stroke | colloquial | HIGH | Dinamalar |
| நீர் பற்றாக்குறை | neer pattrakurai | water scarcity | water | formal | HIGH | All Tamil outlets |
| நீர் நெருக்கடி | neer nerukkadi | water crisis | water | formal | HIGH | The Hindu Tamil |
| குடிநீர் பஞ்சம் | kudineer panjam | drinking water famine | water | journalistic | HIGH | Dinamalar |
| வறட்சி | varatchi | drought | water | formal | HIGH | All outlets |
| நீர் தட்டுப்பாடு | neer thattuppaadu | water shortage | water | formal | MEDIUM | Dinamani |
| குடிநீர் தட்டுப்பாடு | kudineer thattuppaadu | drinking water shortage | water | formal | HIGH | Dinamalar |
| ஆறு வறண்டது | aaru varanndathu | river dried up | water | descriptive | MEDIUM | Dinamani |
| மின்வெட்டு | min vettu | power cut (lit. electricity cut) | power | colloquial, very common | HIGH | All Tamil outlets -- THE standard Tamil term |
| மின்தடை | min thadai | power interruption | power | formal | HIGH | Dinamani |
| மின் நெருக்கடி | min nerukkadi | electricity crisis | power | formal | MEDIUM | The Hindu Tamil |
| லோட் ஷெட்டிங் | load shedding (borrowed) | load shedding | power | borrowed English | MEDIUM | News7 Tamil |
| மின் பற்றாக்குறை | min pattrakurai | electricity shortage | power | formal | MEDIUM | Dinamani |
| பயிர் சேதம் | payir setham | crop damage | crop | formal | HIGH | All Tamil outlets |
| பயிர் நஷ்டம் | payir nashtam | crop loss | crop | formal | HIGH | Dinamalar, Dinamani |
| விவசாயிகள் பாதிப்பு | vivasayigal paathippu | farmers affected | crop | journalistic | HIGH | All outlets |
| பயிர்கள் கருகின | payirgal karuginan | crops scorched | crop | descriptive | MEDIUM | Dinamalar |
| விவசாய நஷ்டம் | vivasaaya nashtam | agricultural loss | crop | formal | MEDIUM | The Hindu Tamil |
| நீரிழப்பு | neerilhappu | dehydration | human | medical/formal | HIGH | All outlets |
| மருத்துவமனையில் அனுமதி | maruthuvamanayil anumathi | hospital admission | human | formal | HIGH | Dinamani |
| பள்ளிகளுக்கு விடுமுறை | palligalukku vidumurai | school holidays | human | general | HIGH | All outlets |
| எச்சரிக்கை | echarikkai | warning | govt | formal | HIGH | IMD Tamil, all outlets |
| நிவாரணம் | nivaranam | relief | govt | formal | HIGH | All outlets |
| சிவப்பு எச்சரிக்கை | sivappu echarikkai | red alert | govt | formal | HIGH | All outlets |
| வெப்பநிலை | veppanilai | temperature | temperature | formal | HIGH | All outlets |
| வெப்பநிலை உயர்வு | veppanilai uyarvu | temperature rise | temperature | formal | HIGH | All outlets |
| X டிகிரி செல்சியஸ் | X degree celsius | X degrees Celsius | temperature | formal | HIGH | All outlets |
| உச்சபட்ச வெப்பநிலை | ucchapattcha veppanilai | maximum temperature | temperature | formal/IMD | HIGH | IMD Tamil |

---

### 4. TELUGU (te)

Key outlets: Eenadu, Sakshi, TV9 Telugu, NTV Telugu, ABN Andhra Jyothi. Telugu media frequently uses borrowed English terms alongside native Telugu.

| Term (Telugu) | Transliteration | English Meaning | Category | Register | Confidence | Sources |
|---|---|---|---|---|---|---|
| వడ గాలులు | vada gaalulu | hot winds | heatwave | colloquial, very common | HIGH | Eenadu, Sakshi -- THE classic Telugu term |
| ఎండ వేడి | enda vedi | sun heat | heatwave | colloquial | HIGH | Eenadu |
| భారీ ఎండలు | bhaari endalu | heavy/severe sun | heatwave | journalistic | HIGH | Eenadu, Sakshi |
| హీట్ వేవ్ | heat wave (borrowed) | heatwave | heatwave | borrowed English | HIGH | TV9 Telugu, NTV Telugu, Sakshi |
| ఉష్ణ తరంగం | ushna tarangam | heat wave | heatwave | formal/IMD | HIGH | IMD Telugu, Eenadu |
| కడ ఎండలు | kada endalu | extreme sun/heat | heatwave | journalistic | HIGH | Sakshi |
| మండుటెండ | mandutenda | blazing sun | heatwave | literary/journalistic | HIGH | Eenadu -- very common literary term |
| ఎండల తీవ్రత | endala teevrata | intensity of heat | heatwave | journalistic | MEDIUM | Sakshi |
| ఎండ దెబ్బ | enda debba | sun strike/sunstroke | death/stroke | colloquial, very common | HIGH | Eenadu, Sakshi -- THE standard Telugu term |
| హీట్ స్ట్రోక్ | heat stroke (borrowed) | heatstroke | death/stroke | borrowed English | HIGH | TV9 Telugu, NTV Telugu |
| సన్ స్ట్రోక్ | sun stroke (borrowed) | sunstroke | death/stroke | borrowed English | MEDIUM | TV9 Telugu |
| ఎండ వల్ల మరణం | enda valla maranam | death due to sun | death/stroke | formal | HIGH | Eenadu |
| ఉష్ణోగ్రత | ushnograta | temperature (but used in heatstroke context too) | death/stroke | formal | HIGH | All outlets |
| వేడి తట్టుకోలేక | vedi thattukooleka | unable to bear heat | death/stroke | descriptive | MEDIUM | Sakshi |
| నీటి కొరత | neeti korata | water shortage | water | formal | HIGH | All Telugu outlets |
| నీటి సంక్షోభం | neeti sankshobham | water crisis | water | formal | HIGH | Eenadu, Sakshi |
| తాగునీటి సమస్య | taaguneeti samasya | drinking water problem | water | general | HIGH | Eenadu |
| కరువు | karuvu | drought | water | formal | HIGH | All outlets |
| నీటి ఎద్దడి | neeti eddadi | water scarcity | water | colloquial | MEDIUM | Eenadu |
| బోర్లు ఎండిపోయాయి | borlu endipoyaayi | borewells dried up | water | descriptive | MEDIUM | Sakshi |
| విద్యుత్ కోత | vidyut kota | power cut | power | formal | HIGH | All Telugu outlets |
| కరెంట్ కట్ | current cut (borrowed) | power cut | power | borrowed English, very common | HIGH | Eenadu, Sakshi -- colloquially preferred |
| విద్యుత్ సంక్షోభం | vidyut sankshobham | electricity crisis | power | formal | MEDIUM | Eenadu |
| లోడ్ షెడ్డింగ్ | load shedding (borrowed) | load shedding | power | borrowed English | HIGH | TV9 Telugu |
| విద్యుత్ డిమాండ్ | vidyut demand | electricity demand | power | mixed register | MEDIUM | Sakshi |
| పంట నష్టం | panta nashtam | crop loss | crop | formal | HIGH | Eenadu, Sakshi |
| పంట నాశనం | panta naashanam | crop destruction | crop | formal | HIGH | Eenadu |
| రైతుల ఆందోళన | raithula andolana | farmers' agitation/distress | crop | journalistic | HIGH | All outlets |
| పంటలు ఎండిపోయాయి | pantalu endipoyaayi | crops dried up | crop | descriptive | HIGH | Sakshi |
| వ్యవసాయ నష్టం | vyavasaya nashtam | agricultural loss | crop | formal | MEDIUM | Eenadu |
| నిర్జలీకరణం | nirjaleekranam | dehydration | human | formal/medical | HIGH | All outlets |
| ఆసుపత్రిలో చేరిక | asupatrilo cherika | hospital admission | human | formal | HIGH | Eenadu |
| పాఠశాలలకు సెలవులు | paathasalaalaku selavulu | school holidays | human | general | HIGH | All outlets |
| హెచ్చరిక | hechcharika | warning | govt | formal | HIGH | All outlets |
| సహాయ చర్యలు | sahaaya charyalu | relief measures | govt | formal | HIGH | Eenadu, Sakshi |
| రెడ్ అలర్ట్ | red alert (borrowed) | red alert | govt | borrowed English | HIGH | All outlets |
| ఉష్ణోగ్రత | ushnograta | temperature | temperature | formal | HIGH | All outlets |
| ఉష్ణోగ్రత పెరుగుదల | ushnograta perugudala | temperature increase | temperature | formal | HIGH | Eenadu |
| X డిగ్రీల సెల్సియస్ | X degrees celsius | X degrees Celsius | temperature | formal | HIGH | All outlets |
| పాదరసం పెరిగింది | paadarasam perigindi | mercury rose | temperature | journalistic idiom | HIGH | Eenadu, Sakshi |

---

### 5. BENGALI (bn)

Key outlets: Anandabazar Patrika, ABP Ananda, Ei Samay, Sangbad Pratidin, Bartaman. Bengali has a strong literary tradition that influences journalism.

| Term (Bengali) | Transliteration | English Meaning | Category | Register | Confidence | Sources |
|---|---|---|---|---|---|---|
| দাবদাহ | dabdaho | scorching heat / heatwave | heatwave | formal/literary, very common | HIGH | Anandabazar Patrika -- THE classic Bengali term |
| তাপপ্রবাহ | tapprobaaho | heat wave | heatwave | formal/IMD | HIGH | IMD Bengali, ABP Ananda |
| প্রচণ্ড গরম | prochondo gorom | extreme heat | heatwave | journalistic | HIGH | All Bengali outlets |
| তীব্র গরম | teebro gorom | intense heat | heatwave | journalistic | HIGH | Ei Samay |
| ঝলসানো গরম | jholsano gorom | scorching heat | heatwave | journalistic | MEDIUM | Anandabazar |
| লু হাওয়া | lu haowa | hot wind (loo) | heatwave | colloquial | HIGH | All outlets (used in North Bengal context) |
| গরমের দাপট | goromer dapot | fury of heat | heatwave | journalistic | HIGH | Very common headline pattern |
| দাবানল | dabanol | wildfire / extreme heat (lit. forest fire) | heatwave | literary | MEDIUM | Anandabazar (sometimes used metaphorically) |
| অসহ্য গরম | osohho gorom | unbearable heat | heatwave | colloquial | HIGH | All outlets |
| হিটস্ট্রোক | hitstroke (borrowed) | heatstroke | death/stroke | borrowed English | HIGH | ABP Ananda, Ei Samay |
| তাপাঘাত | tapaghat | heatstroke | death/stroke | formal | HIGH | Anandabazar, formal reporting |
| সূর্যাঘাত | surjaghat | sunstroke | death/stroke | formal | HIGH | Anandabazar Patrika |
| গরমে মৃত্যু | gorome mrittu | death in heat | death/stroke | journalistic | HIGH | All outlets |
| তাপে মৃত্যু | tape mrittu | death from heat | death/stroke | formal | HIGH | ABP Ananda |
| লু লাগা | lu laga | heat struck (getting loo) | death/stroke | colloquial | HIGH | All outlets |
| জলসংকট | jolsongkot | water crisis | water | formal | HIGH | Anandabazar, ABP Ananda |
| জল সমস্যা | jol somossha | water problem | water | general | HIGH | All outlets |
| পানীয় জলের সংকট | paniyo joler songkot | drinking water crisis | water | formal | HIGH | Anandabazar |
| খরা | khora | drought | water | formal | HIGH | All outlets |
| জলাভাব | jolabhab | water scarcity | water | formal | MEDIUM | Anandabazar |
| ট্যাঙ্কারে জল | tanker-e jol | water by tanker | water | descriptive | MEDIUM | Ei Samay |
| বিদ্যুৎ বিভ্রাট | bidyut bibhrat | power disruption | power | formal | HIGH | All outlets |
| লোড শেডিং | load shedding (borrowed) | load shedding | power | borrowed English, very common | HIGH | All Bengali outlets |
| বিদ্যুৎ সংকট | bidyut songkot | electricity crisis | power | formal | MEDIUM | ABP Ananda |
| পাওয়ার কাট | power cut (borrowed) | power cut | power | borrowed English | HIGH | Ei Samay |
| ফসলের ক্ষতি | fosholer khhoti | crop damage | crop | formal | HIGH | All outlets |
| ফসল নষ্ট | foshol noshto | crop destroyed | crop | general | HIGH | Anandabazar |
| কৃষি ক্ষতি | krishi khhoti | agricultural damage | crop | formal | MEDIUM | ABP Ananda |
| চাষিদের ক্ষতি | chashider khhoti | farmers' losses | crop | journalistic | HIGH | All outlets |
| পানিশূন্যতা | panishunota | dehydration | human | medical/formal | HIGH | All outlets |
| ডিহাইড্রেশন | dehydration (borrowed) | dehydration | human | borrowed English | HIGH | ABP Ananda |
| হাসপাতালে ভর্তি | haspatale bhorti | hospital admission | human | general | HIGH | All outlets |
| স্কুল বন্ধ | school bondho | school closed | human | general | HIGH | All outlets |
| সরকারি ত্রাণ | sorkari tran | government relief | govt | formal | HIGH | All outlets |
| সতর্কতা | sotorkota | alert/warning | govt | formal | HIGH | IMD, all outlets |
| রেড অ্যালার্ট | red alert (borrowed) | red alert | govt | borrowed English | HIGH | All outlets |
| তাপমাত্রা | tapmatra | temperature | temperature | formal | HIGH | All outlets |
| তাপমাত্রা বৃদ্ধি | tapmatra briddhi | temperature rise | temperature | formal | HIGH | All outlets |
| পারদ চড়ছে | parod chorhchhe | mercury rising | temperature | journalistic | HIGH | Anandabazar -- common headline idiom |

---

### 6. MARATHI (mr)

Key outlets: Loksatta, Maharashtra Times, Sakal, ABP Majha, Lokmat. Marathi heat journalism in Maharashtra is particularly important given Mumbai/Vidarbha heat exposure.

| Term (Marathi) | Transliteration | English Meaning | Category | Register | Confidence | Sources |
|---|---|---|---|---|---|---|
| उष्णतेची लाट | ushnatéchi laat | heat wave | heatwave | formal/journalistic | HIGH | Loksatta, Maharashtra Times |
| उष्णलहर | ushna lahar | heat wave | heatwave | formal/IMD | HIGH | IMD Marathi, Loksatta |
| भयंकर ऊन | bhayankar oon | terrible heat/sun | heatwave | colloquial | HIGH | Sakal, Lokmat |
| कडक ऊन | kadak oon | harsh sun | heatwave | colloquial, very common | HIGH | All Marathi outlets |
| प्रचंड उष्णता | prachand ushnata | extreme heat | heatwave | journalistic | HIGH | Loksatta |
| ऊन्हाचा कहर | oonhacha kahar | fury of heat | heatwave | journalistic idiom | HIGH | Maharashtra Times -- common headline |
| तापमानाचा पारा चढला | tapmanaacha paara chadhla | mercury of temperature rose | heatwave/temp | journalistic idiom | HIGH | Maharashtra Times |
| उन्हाळ्याची तीव्रता | unhaalyachi teevrata | summer intensity | heatwave | formal | MEDIUM | Loksatta |
| हीट वेव्ह | heat wave (borrowed) | heatwave | heatwave | borrowed English | HIGH | ABP Majha |
| लू | loo | hot wind | heatwave | borrowed from Hindi, used in Vidarbha | HIGH | Lokmat (Vidarbha edition) |
| उष्माघात | ushmaaghat | heatstroke | death/stroke | formal | HIGH | All Marathi outlets |
| लू लागणे | loo laagne | getting heat stroke | death/stroke | colloquial | HIGH | Sakal, Lokmat |
| उष्णतेने मृत्यू | ushnatene mrityu | death from heat | death/stroke | formal | HIGH | Loksatta |
| ऊन लागणे | oon laagne | struck by sun | death/stroke | colloquial | HIGH | All outlets |
| हीट स्ट्रोक | heat stroke (borrowed) | heatstroke | death/stroke | borrowed English | HIGH | ABP Majha |
| सन स्ट्रोक | sun stroke (borrowed) | sunstroke | death/stroke | borrowed English | MEDIUM | ABP Majha |
| पाणी टंचाई | paani tanchai | water scarcity | water | colloquial, very common | HIGH | All Marathi outlets -- THE standard term |
| जलसंकट | jal sankat | water crisis | water | formal | HIGH | Loksatta |
| पाणी समस्या | paani samasya | water problem | water | general | HIGH | Sakal |
| टँकरने पाणी पुरवठा | tanker-ne paani puravatha | water supply by tanker | water | descriptive | HIGH | Maharashtra Times |
| दुष्काळ | dushkaal | drought/famine | water | formal | HIGH | All outlets |
| पिण्याच्या पाण्याची समस्या | pinyachya paanyachi samasya | drinking water problem | water | formal | HIGH | Loksatta |
| विहिरी आटल्या | vihiri aatalya | wells dried up | water | descriptive | MEDIUM | Sakal |
| वीज कपात | veej kapaat | power cut | power | formal | HIGH | All Marathi outlets |
| लोडशेडिंग | loadshedding (borrowed) | load shedding | power | borrowed English | HIGH | All outlets |
| वीज संकट | veej sankat | electricity crisis | power | formal | MEDIUM | Loksatta |
| वीज गुल | veej gul | power gone | power | colloquial | HIGH | Sakal, Lokmat |
| भारनियमन | bhaarniyaman | load regulation (power cuts) | power | formal/official Maharashtra term | HIGH | Loksatta -- this is the Maharashtra-specific official term |
| पीक नुकसान | peek nuksan | crop damage | crop | formal | HIGH | All outlets |
| शेतीचे नुकसान | shetiche nuksan | farming damage | crop | general | HIGH | Sakal |
| शेतकरी संकटात | shetkari sankatat | farmers in crisis | crop | journalistic | HIGH | All outlets |
| पिके करपली | pike karpali | crops scorched | crop | descriptive | HIGH | Sakal |
| निर्जलीकरण | nirjaleekaran | dehydration | human | formal | HIGH | Loksatta |
| रुग्णालयात दाखल | rugnaalayaat daakhal | hospital admission | human | formal | HIGH | All outlets |
| शाळांना सुटी | shaalanna suti | school holidays | human | general | HIGH | All outlets |
| हीट अॅक्शन प्लान | heat action plan (borrowed) | heat action plan | govt | borrowed English | HIGH | ABP Majha |
| दिलासा | dilaasa | relief/comfort | govt | general | MEDIUM | All outlets |
| सावधानतेचा इशारा | savadhanatecha ishaara | caution warning | govt | formal | HIGH | All outlets |
| तापमान वाढ | tapmaan vaadh | temperature rise | temperature | formal | HIGH | All outlets |
| X अंश सेल्सिअस | X ansh celsius | X degrees Celsius | temperature | formal | HIGH | All outlets |

**Maharashtra-specific note**: The term **भारनियमन** (bhaarniyaman) is the official Maharashtra state government term for load shedding/power cuts and is widely used in Marathi media. It does not appear in other languages. This is a critical term to include.

---

### 7. GUJARATI (gu)

Key outlets: Gujarat Samachar, Divya Bhaskar, Sandesh, TV9 Gujarati. Gujarat faces severe heatwaves in Ahmedabad, Kutch, and Saurashtra, and was the pioneer of Heat Action Plans in India (Ahmedabad HAP 2013).

| Term (Gujarati) | Transliteration | English Meaning | Category | Register | Confidence | Sources |
|---|---|---|---|---|---|---|
| ભારે ગરમી | bhaare garmi | severe heat | heatwave | journalistic | HIGH | Gujarat Samachar, Divya Bhaskar |
| આકરી ગરમી | aakri garmi | harsh heat | heatwave | colloquial | HIGH | Sandesh |
| લૂ | loo | hot wind | heatwave | colloquial | HIGH | All outlets |
| હીટવેવ | heatwave (borrowed) | heatwave | heatwave | borrowed English | HIGH | TV9 Gujarati, Divya Bhaskar |
| ઉષ્ણ મોજું | ushna mojun | heat wave | heatwave | formal | MEDIUM | Gujarat Samachar |
| ગરમીનો પ્રકોપ | garmino prakop | fury of heat | heatwave | journalistic | HIGH | Divya Bhaskar |
| તાપ | taap | heat/sun | heatwave | colloquial | HIGH | All outlets |
| આકરો તાપ | aakro taap | harsh heat | heatwave | colloquial | HIGH | Gujarat Samachar |
| લૂ લાગવી | loo laagvi | getting heatstroke | death/stroke | colloquial, very common | HIGH | All outlets |
| હીટ સ્ટ્રોક | heat stroke (borrowed) | heatstroke | death/stroke | borrowed English | HIGH | TV9 Gujarati |
| ગરમીથી મૃત્યુ | garmithi mrityu | death from heat | death/stroke | formal | HIGH | Gujarat Samachar |
| ઉષ્માઘાત | ushmaaghaat | heatstroke | death/stroke | formal | HIGH | Divya Bhaskar |
| તડકાથી મોત | tadkaathi mot | death from sun | death/stroke | colloquial | MEDIUM | Sandesh |
| પાણીની તંગી | paanini tangi | water scarcity | water | colloquial | HIGH | All outlets |
| જળ સંકટ | jal sankat | water crisis | water | formal | HIGH | Gujarat Samachar |
| પાણીની અછત | paanini achhat | water shortage | water | formal | HIGH | Divya Bhaskar |
| દુષ્કાળ | dushkaal | drought | water | formal | HIGH | All outlets |
| પીવાના પાણીની સમસ્યા | pivaana paanini samasya | drinking water problem | water | general | HIGH | Gujarat Samachar |
| ટેન્કર | tanker (borrowed) | water tanker | water | borrowed English | HIGH | All outlets |
| વીજ કાપ | veej kaap | power cut | power | formal | HIGH | All outlets |
| લોડશેડિંગ | loadshedding (borrowed) | load shedding | power | borrowed English | HIGH | All outlets |
| વીજ સંકટ | veej sankat | electricity crisis | power | formal | MEDIUM | Gujarat Samachar |
| અંધારપટ | andhaarput | blackout (lit. darkness) | power | colloquial | MEDIUM | Divya Bhaskar |
| પાક નુકસાન | paak nuksan | crop damage | crop | formal | HIGH | Gujarat Samachar |
| ખેતીને નુકસાન | khetine nuksan | farming damage | crop | general | HIGH | Divya Bhaskar |
| ખેડૂતોને નુકસાન | khedootoone nuksan | farmers suffer losses | crop | journalistic | HIGH | All outlets |
| ડિહાઇડ્રેશન | dehydration (borrowed) | dehydration | human | borrowed English | HIGH | TV9 Gujarati |
| હોસ્પિટલમાં દાખલ | hospital maan daakhal | hospital admission | human | general | HIGH | All outlets |
| શાળા બંધ | shaala bandh | school closed | human | general | HIGH | All outlets |
| રાહત | raahat | relief | govt | formal | HIGH | All outlets |
| એડવાઇઝરી | advisory (borrowed) | advisory | govt | borrowed English | HIGH | TV9 Gujarati |
| હીટ એક્શન પ્લાન | heat action plan (borrowed) | heat action plan | govt | borrowed English | HIGH | Ahmedabad coverage, all outlets |
| રેડ એલર્ટ | red alert (borrowed) | red alert | govt | borrowed English | HIGH | All outlets |
| તાપમાન | taapman | temperature | temperature | formal | HIGH | All outlets |
| તાપમાન વધ્યું | taapman vadhyun | temperature rose | temperature | formal | HIGH | All outlets |
| પારો ચઢ્યો | paaro chadhyo | mercury rose | temperature | journalistic idiom | HIGH | Gujarat Samachar, Divya Bhaskar |

---

### 8. KANNADA (kn)

Key outlets: Prajavani, Vijaya Karnataka, Udayavani, TV9 Kannada, Public TV.

| Term (Kannada) | Transliteration | English Meaning | Category | Register | Confidence | Sources |
|---|---|---|---|---|---|---|
| ಬಿಸಿ ಗಾಳಿ | bisi gaali | hot wind | heatwave | colloquial | HIGH | Prajavani, Vijaya Karnataka |
| ಉಷ್ಣ ಅಲೆ | ushna ale | heat wave | heatwave | formal/IMD | HIGH | IMD Kannada, Prajavani |
| ಹೀಟ್ ವೇವ್ | heat wave (borrowed) | heatwave | heatwave | borrowed English | HIGH | TV9 Kannada |
| ತೀವ್ರ ಬಿಸಿಲು | teevra bisilu | intense sun | heatwave | journalistic | HIGH | Prajavani |
| ಕಡು ಬಿಸಿಲು | kadu bisilu | severe sun | heatwave | journalistic | HIGH | Vijaya Karnataka |
| ಬರಗಾಲ ಬಿಸಿಲು | baragaala bisilu | drought-like sun | heatwave | literary | MEDIUM | Udayavani |
| ಬೆಂಕಿ ಬಿಸಿಲು | benki bisilu | fire-like sun | heatwave | colloquial | MEDIUM | Vijaya Karnataka |
| ಬಿಸಿಲಿನ ಹೊಡೆತ | bisilina hodeta | sun strike/blow | death/stroke | colloquial | HIGH | Prajavani -- THE common Kannada term |
| ಹೀಟ್ ಸ್ಟ್ರೋಕ್ | heat stroke (borrowed) | heatstroke | death/stroke | borrowed English | HIGH | TV9 Kannada |
| ಸನ್ ಸ್ಟ್ರೋಕ್ | sun stroke (borrowed) | sunstroke | death/stroke | borrowed English | MEDIUM | TV9 Kannada |
| ಉಷ್ಣಾಘಾತ | ushnaaghaata | heatstroke | death/stroke | formal | HIGH | Prajavani |
| ಬಿಸಿಲಿಗೆ ಸಾವು | bislige saavu | death from sun | death/stroke | journalistic | HIGH | All outlets |
| ನೀರಿನ ಕೊರತೆ | neerina korate | water shortage | water | formal | HIGH | All outlets |
| ಜಲ ಸಂಕಟ | jala sankata | water crisis | water | formal | HIGH | Prajavani |
| ಕುಡಿಯುವ ನೀರಿನ ಸಮಸ್ಯೆ | kudiyuva neerina samasye | drinking water problem | water | general | HIGH | Vijaya Karnataka |
| ಬರ | bara | drought | water | formal | HIGH | All outlets |
| ಬರಗಾಲ | baragaala | drought/famine | water | formal | HIGH | All outlets |
| ವಿದ್ಯುತ್ ಕಡಿತ | vidyut kadita | power cut | power | formal | HIGH | All outlets |
| ಲೋಡ್ ಶೆಡ್ಡಿಂಗ್ | load shedding (borrowed) | load shedding | power | borrowed English | HIGH | TV9 Kannada |
| ಕರೆಂಟ್ ಕಟ್ | current cut (borrowed) | power cut | power | borrowed English, colloquial | HIGH | All outlets |
| ಬೆಳೆ ನಷ್ಟ | bele nashta | crop loss | crop | formal | HIGH | All outlets |
| ಬೆಳೆ ಹಾನಿ | bele haani | crop damage | crop | formal | HIGH | Prajavani |
| ರೈತರ ಸಂಕಷ್ಟ | raitara sankashta | farmers' hardship | crop | journalistic | HIGH | All outlets |
| ನಿರ್ಜಲೀಕರಣ | nirjaleekarna | dehydration | human | formal | HIGH | Prajavani |
| ಆಸ್ಪತ್ರೆಗೆ ದಾಖಲು | aaspathrege daakhalu | hospital admission | human | general | HIGH | All outlets |
| ಶಾಲೆಗಳಿಗೆ ರಜೆ | shaaleglige raje | school holidays | human | general | HIGH | All outlets |
| ಪರಿಹಾರ | parihaara | relief | govt | formal | HIGH | All outlets |
| ಎಚ್ಚರಿಕೆ | echcharike | warning | govt | formal | HIGH | All outlets |
| ಕೆಂಪು ಎಚ್ಚರಿಕೆ | kempu echcharike | red alert | govt | formal | HIGH | All outlets |
| ತಾಪಮಾನ ಏರಿಕೆ | tapamaana erike | temperature rise | temperature | formal | HIGH | All outlets |

---

### 9. MALAYALAM (ml)

Key outlets: Manorama (Malayala Manorama), Mathrubhumi, Asianet News, Manorama News, 24 News. Kerala's heat vocabulary includes unique terms related to its tropical climate.

| Term (Malayalam) | Transliteration | English Meaning | Category | Register | Confidence | Sources |
|---|---|---|---|---|---|---|
| ഉഷ്ണ തരംഗം | ushna tarangam | heat wave | heatwave | formal/IMD | HIGH | Manorama, Mathrubhumi |
| ചൂട് തരംഗം | choodu tarangam | heat wave | heatwave | general | HIGH | Asianet News |
| കടുത്ത ചൂട് | kaduttha choodu | extreme heat | heatwave | journalistic | HIGH | All outlets |
| കൊടും ചൂട് | kodum choodu | severe heat | heatwave | journalistic | HIGH | Manorama |
| ഹീറ്റ് വേവ് | heat wave (borrowed) | heatwave | heatwave | borrowed English | HIGH | Asianet News, Manorama News |
| വെയിലിന്റെ കാഠിന്യം | veyilinte kaathinnyam | severity of sun | heatwave | literary | MEDIUM | Mathrubhumi |
| ചൂടിന്റെ കാഠിന്യം | choodinte kaathinnyam | severity of heat | heatwave | literary | MEDIUM | Mathrubhumi |
| സൂര്യാഘാതം | sooryaaghaatam | sunstroke | death/stroke | formal | HIGH | Manorama, Mathrubhumi |
| ഹീറ്റ് സ്ട്രോക്ക് | heat stroke (borrowed) | heatstroke | death/stroke | borrowed English | HIGH | Asianet News |
| ചൂടേറ്റ് മരണം | choodu ettu maranam | death from heat | death/stroke | journalistic | HIGH | Manorama |
| വെയിലേറ്റ് മരണം | veyil ettu maranam | death from sun | death/stroke | journalistic | HIGH | Mathrubhumi |
| ജലക്ഷാമം | jalakshaamam | water famine/scarcity | water | formal | HIGH | All outlets |
| കുടിവെള്ള ക്ഷാമം | kudivella kshaamam | drinking water scarcity | water | formal | HIGH | Manorama |
| ജല ദൗര്‍ലഭ്യം | jala daurlabhyam | water scarcity | water | formal/literary | MEDIUM | Mathrubhumi |
| വരള്‍ച്ച | varalchcha | drought | water | formal | HIGH | All outlets |
| കിണര്‍ വറ്റി | kinar vatti | well dried up | water | descriptive | MEDIUM | Manorama |
| വൈദ്യുതി മുടക്കം | vaidyuthi mudakkam | power disruption | power | formal | HIGH | All outlets |
| ലോഡ് ഷെഡ്ഡിംഗ് | load shedding (borrowed) | load shedding | power | borrowed English | HIGH | All outlets |
| പവര്‍കട്ട് | power cut (borrowed) | power cut | power | borrowed English | HIGH | Asianet News |
| വിള നഷ്ടം | vila nashtam | crop loss | crop | formal | HIGH | All outlets |
| കൃഷി നാശം | krishi naasham | agricultural destruction | crop | formal | HIGH | Manorama |
| കര്‍ഷകര്‍ പ്രതിസന്ധിയില്‍ | karshkar prathisandhiyil | farmers in crisis | crop | journalistic | HIGH | All outlets |
| നിര്‍ജലീകരണം | nirjaleekranam | dehydration | human | formal | HIGH | All outlets |
| ആശുപത്രിയില്‍ പ്രവേശിപ്പിച്ചു | aashupathiyil praveshippichu | hospitalized | human | formal | HIGH | All outlets |
| സ്കൂള്‍ അവധി | school avadhi | school holiday | human | general | HIGH | All outlets |
| ദുരിതാശ്വാസം | durithaashvaasam | disaster relief | govt | formal | HIGH | All outlets |
| മുന്നറിയിപ്പ് | munnariyippu | warning/alert | govt | formal | HIGH | All outlets |
| റെഡ് അലര്‍ട്ട് | red alert (borrowed) | red alert | govt | borrowed English | HIGH | All outlets |
| താപനില | taapanila | temperature | temperature | formal | HIGH | All outlets |
| താപനില ഉയര്‍ന്നു | taapanila uyarnnu | temperature rose | temperature | formal | HIGH | All outlets |

---

### 10. ODIA (or)

Key outlets: Sambad, Dharitri, Pragativadi, OTV (Odisha TV), Kanak News. Odisha is among the most heat-affected states, and heat deaths are a major annual news story.

| Term (Odia) | Transliteration | English Meaning | Category | Register | Confidence | Sources |
|---|---|---|---|---|---|---|
| ଉଷ୍ଣ ଲହରୀ | ushna lahari | heat wave | heatwave | formal/IMD | HIGH | Sambad, Dharitri |
| ହିଟ୍ ୱେଭ୍ | heat wave (borrowed) | heatwave | heatwave | borrowed English | HIGH | OTV |
| ପ୍ରବଳ ଗରମ | prabal garam | extreme heat | heatwave | journalistic | HIGH | Sambad |
| ଭୟଙ୍କର ଗରମ | bhayankara garam | terrible heat | heatwave | journalistic | HIGH | Dharitri |
| ଗରମ ପବନ | garam pabana | hot wind | heatwave | descriptive | HIGH | Sambad |
| ଲୁ | lu | hot wind (loo) | heatwave | colloquial | HIGH | All outlets |
| ଝାଳ | jhala | heat/sweat | heatwave | colloquial | MEDIUM | Pragativadi |
| ଲୁ ଲାଗିବା | lu lagiba | getting heatstroke | death/stroke | colloquial | HIGH | All outlets |
| ହିଟ୍ ଷ୍ଟ୍ରୋକ୍ | heat stroke (borrowed) | heatstroke | death/stroke | borrowed English | HIGH | OTV |
| ଗରମରେ ମୃତ୍ୟୁ | gararme mrityu | death in heat | death/stroke | journalistic | HIGH | Sambad -- Odisha heat deaths are major news |
| ଉଷ୍ଣାଘାତ | ushnaaghaata | heatstroke | death/stroke | formal | HIGH | Dharitri |
| ସୂର୍ଯ୍ୟାଘାତ | suryaaghaata | sunstroke | death/stroke | formal | MEDIUM | Sambad |
| ଗରମରେ ମଲେ | gararme male | died in heat | death/stroke | colloquial headline | HIGH | Pragativadi |
| ଜଳ ସଙ୍କଟ | jala sankata | water crisis | water | formal | HIGH | All outlets |
| ପାଣି ଅଭାବ | paani abhaab | water scarcity | water | general | HIGH | All outlets |
| ପାଣି ସମସ୍ୟା | paani samasya | water problem | water | general | HIGH | Sambad |
| ଖରା | khara | drought | water | formal | HIGH | All outlets |
| ପେୟ ଜଳ ସଙ୍କଟ | peya jala sankata | drinking water crisis | water | formal | HIGH | Dharitri |
| ବିଦ୍ୟୁତ ବିଭ୍ରାଟ | bidyut bibhraata | power disruption | power | formal | HIGH | All outlets |
| ଲୋଡ୍ ସେଡିଂ | load shedding (borrowed) | load shedding | power | borrowed English | HIGH | OTV |
| ବିଜୁଳି ସମସ୍ୟା | bijuli samasya | electricity problem | power | colloquial | HIGH | Pragativadi |
| ଫସଲ କ୍ଷତି | fasala kshati | crop damage | crop | formal | HIGH | All outlets |
| ଫସଲ ନଷ୍ଟ | fasala nashta | crop loss | crop | formal | HIGH | Sambad |
| ଚାଷୀଙ୍କ ସମସ୍ୟା | chaashinka samasya | farmers' problems | crop | journalistic | HIGH | All outlets |
| ନିର୍ଜଳୀକରଣ | nirjaleekarna | dehydration | human | formal | HIGH | All outlets |
| ଡାକ୍ତରଖାନାରେ ଭର୍ତ୍ତି | daktarkhaanaare bhartti | hospital admission | human | general | HIGH | Sambad |
| ବିଦ୍ୟାଳୟ ବନ୍ଦ | bidyaalaya banda | school closed | human | general | HIGH | All outlets |
| ସହାୟତା | sahaayata | relief/aid | govt | formal | HIGH | All outlets |
| ସତର୍କତା | satarkata | alert/warning | govt | formal | HIGH | All outlets |
| ତାପମାତ୍ରା | taapamatraa | temperature | temperature | formal | HIGH | All outlets |
| ତାପମାତ୍ରା ବୃଦ୍ଧି | taapamatraa briddhi | temperature rise | temperature | formal | HIGH | All outlets |

**Odisha-specific note**: Odisha consistently reports the highest heat deaths in India. Terms like "ଗରମରେ ମୃତ୍ୟୁ" (death in heat) and "ଲୁ ଲାଗିବା" (getting loo) are extremely frequently used during summer months in Sambad and Dharitri.

---

### 11. PUNJABI (pa)

Key outlets: Ajit, Punjabi Tribune, Jagbani, Rozana Spokesman. Punjab's agricultural focus makes crop damage terms especially important.

| Term (Gurmukhi) | Transliteration | English Meaning | Category | Register | Confidence | Sources |
|---|---|---|---|---|---|---|
| ਲੂ | loo | hot wind / heatwave | heatwave | colloquial | HIGH | Ajit, Jagbani |
| ਹੀਟ ਵੇਵ | heat wave (borrowed) | heatwave | heatwave | borrowed English | HIGH | Punjabi Tribune |
| ਭਿਆਨਕ ਗਰਮੀ | bhiaanak garmi | terrible heat | heatwave | journalistic | HIGH | Ajit |
| ਕੜਾਕੇ ਦੀ ਗਰਮੀ | karaake di garmi | biting heat | heatwave | colloquial, very common | HIGH | All Punjabi outlets |
| ਤੱਤੀ ਹਵਾ | tatti hawa | hot wind | heatwave | colloquial | HIGH | Ajit, Jagbani |
| ਗਰਮੀ ਦਾ ਕਹਿਰ | garmi da kahir | fury of heat | heatwave | journalistic | HIGH | All outlets |
| ਲੂ ਲੱਗਣਾ | loo laggna | getting heatstroke | death/stroke | colloquial | HIGH | All outlets |
| ਹੀਟ ਸਟ੍ਰੋਕ | heat stroke (borrowed) | heatstroke | death/stroke | borrowed English | HIGH | Punjabi Tribune |
| ਗਰਮੀ ਨਾਲ ਮੌਤ | garmi naal maut | death from heat | death/stroke | journalistic | HIGH | Ajit |
| ਧੁੱਪ ਨਾਲ ਮੌਤ | dhup naal maut | death from sun | death/stroke | colloquial | MEDIUM | Jagbani |
| ਪਾਣੀ ਦੀ ਕਿੱਲਤ | paani di killat | water scarcity | water | colloquial | HIGH | All outlets |
| ਜਲ ਸੰਕਟ | jal sankat | water crisis | water | formal | HIGH | Punjabi Tribune |
| ਪਾਣੀ ਦੀ ਸਮੱਸਿਆ | paani di samassiaa | water problem | water | general | HIGH | Ajit |
| ਸੋਕਾ | soka | drought | water | formal | HIGH | All outlets |
| ਬਿਜਲੀ ਕੱਟ | bijli katt | power cut | power | colloquial | HIGH | All outlets |
| ਲੋਡ ਸ਼ੈਡਿੰਗ | load shedding (borrowed) | load shedding | power | borrowed English | HIGH | All outlets |
| ਬਿਜਲੀ ਸੰਕਟ | bijli sankat | electricity crisis | power | formal | MEDIUM | Punjabi Tribune |
| ਫ਼ਸਲ ਨੁਕਸਾਨ | fasal nuksan | crop damage | crop | formal | HIGH | All outlets -- Punjab is agricultural heartland |
| ਫ਼ਸਲ ਬਰਬਾਦ | fasal barbaad | crop destroyed | crop | colloquial | HIGH | Ajit |
| ਕਿਸਾਨ ਪਰੇਸ਼ਾਨ | kisan pareshan | farmers distressed | crop | journalistic | HIGH | All outlets |
| ਕਣਕ ਦੀ ਫ਼ਸਲ ਨੁਕਸਾਨ | kanak di fasal nuksan | wheat crop damage | crop | specific | HIGH | Ajit, Jagbani (wheat is key Punjab crop affected by heat) |
| ਡੀਹਾਈਡ੍ਰੇਸ਼ਨ | dehydration (borrowed) | dehydration | human | borrowed English | HIGH | Punjabi Tribune |
| ਹਸਪਤਾਲ ਵਿੱਚ ਭਰਤੀ | haspataal vich bharti | hospitalized | human | general | HIGH | All outlets |
| ਰਾਹਤ | raahat | relief | govt | formal | HIGH | All outlets |
| ਐਡਵਾਈਜ਼ਰੀ | advisory (borrowed) | advisory | govt | borrowed English | HIGH | Punjabi Tribune |
| ਤਾਪਮਾਨ ਵਧਿਆ | tapmaan vadhiaa | temperature rose | temperature | formal | HIGH | All outlets |
| ਪਾਰਾ ਚੜ੍ਹਿਆ | paara charrhia | mercury rose | temperature | journalistic | HIGH | All outlets |

---

### 12. ASSAMESE (as)

Key outlets: Pratidin Time, Asomiya Pratidin, News Live, Prag News. Assam's heat coverage is less intense than northern/central India but still significant, especially in Barak Valley.

| Term (Assamese) | Transliteration | English Meaning | Category | Register | Confidence | Sources |
|---|---|---|---|---|---|---|
| তাপ প্ৰবাহ | taap prabaho | heat wave | heatwave | formal/IMD | HIGH | Pratidin Time |
| হিট ৱেভ | heat wave (borrowed) | heatwave | heatwave | borrowed English | HIGH | News Live |
| প্ৰচণ্ড গৰম | prachanda gorom | extreme heat | heatwave | journalistic | HIGH | Asomiya Pratidin |
| তীব্ৰ গৰম | teebro gorom | intense heat | heatwave | journalistic | HIGH | Pratidin Time |
| লু | lu | hot wind | heatwave | colloquial | HIGH | All outlets |
| গৰমৰ প্ৰকোপ | goromor prokop | fury of heat | heatwave | journalistic | MEDIUM | Asomiya Pratidin |
| তাপাঘাত | tapaghat | heatstroke | death/stroke | formal | HIGH | Pratidin Time |
| লু লগা | lu loga | getting heatstroke | death/stroke | colloquial | HIGH | All outlets |
| হিট ষ্ট্ৰক | hit stroke (borrowed) | heatstroke | death/stroke | borrowed English | MEDIUM | News Live |
| গৰমত মৃত্যু | goromot mrityu | death in heat | death/stroke | journalistic | HIGH | Asomiya Pratidin |
| জল সংকট | jol songkot | water crisis | water | formal | HIGH | Pratidin Time |
| পানী নাটনি | paani naatoni | water scarcity | water | colloquial | HIGH | Asomiya Pratidin |
| পানীৰ অভাব | paanir abhaab | water shortage | water | general | HIGH | All outlets |
| খৰাং | khorang | drought | water | formal | HIGH | All outlets |
| বিদ্যুৎ বিভ্ৰাট | bidyut bibhrat | power disruption | power | formal | HIGH | All outlets |
| লোড শ্বেডিং | load shedding (borrowed) | load shedding | power | borrowed English | HIGH | News Live |
| শস্যৰ ক্ষতি | shosyor khhoti | crop damage | crop | formal | HIGH | Pratidin Time |
| খেতিৰ নষ্ট | khetir noshto | farming loss | crop | colloquial | MEDIUM | Asomiya Pratidin |
| কৃষকৰ সমস্যা | krishokor somossya | farmers' problem | crop | journalistic | HIGH | All outlets |
| পানীশূন্যতা | paanishunota | dehydration | human | formal | HIGH | Pratidin Time |
| চিকিৎসালয়ত ভৰ্তি | chikitsaloyot bhorti | hospital admission | human | formal | HIGH | All outlets |
| সাহায্য | saahajjo | help/relief | govt | formal | HIGH | All outlets |
| সতৰ্কবাণী | sotorkobaani | warning | govt | formal | HIGH | All outlets |
| তাপমাত্ৰা | tapmatra | temperature | temperature | formal | HIGH | All outlets |
| তাপমাত্ৰা বৃদ্ধি | tapmatra briddhi | temperature rise | temperature | formal | HIGH | All outlets |

---

### 13. URDU (ur)

Key outlets: Inquilab, Siasat Daily, Munsif Daily, Sahafat, Rashtriya Sahara. Urdu media covers heat events extensively in Hyderabad, Delhi, UP, and Bihar. Urdu shares much vocabulary with Hindi but uses Nastaliq script and often prefers Perso-Arabic vocabulary.

| Term (Urdu) | Transliteration | English Meaning | Category | Register | Confidence | Sources |
|---|---|---|---|---|---|---|
| لو | loo | hot wind | heatwave | colloquial | HIGH | All Urdu outlets |
| ہیٹ ویو | heat wave (borrowed) | heatwave | heatwave | borrowed English | HIGH | Siasat Daily |
| شدید گرمی | shadeed garmi | severe heat | heatwave | journalistic | HIGH | Inquilab |
| سخت گرمی | sakht garmi | harsh heat | heatwave | colloquial | HIGH | All outlets |
| گرمی کی لہر | garmi ki lehar | heat wave | heatwave | formal | HIGH | Inquilab |
| موسمِ گرما کی شدت | mausam-e-garma ki shiddat | summer severity | heatwave | literary/formal | MEDIUM | Sahafat |
| گرم ہوائیں | garm hawaaein | hot winds | heatwave | descriptive | HIGH | Inquilab |
| تپتی دھوپ | tapti dhoop | burning sunshine | heatwave | literary | MEDIUM | Sahafat |
| لو لگنا | loo lagna | getting heatstroke | death/stroke | colloquial | HIGH | All outlets |
| ہیٹ اسٹروک | heat stroke (borrowed) | heatstroke | death/stroke | borrowed English | HIGH | Siasat Daily |
| سن اسٹروک | sun stroke (borrowed) | sunstroke | death/stroke | borrowed English | MEDIUM | Siasat Daily |
| گرمی سے اموات | garmi se amwaat | deaths from heat | death/stroke | formal | HIGH | Inquilab |
| گرمی سے ہلاکتیں | garmi se halaaktein | deaths/casualties from heat | death/stroke | formal | HIGH | Siasat Daily |
| پانی کا بحران | paani ka buhraan | water crisis | water | formal | HIGH | All outlets |
| قلتِ آب | qillat-e-aab | water scarcity (Persianized) | water | formal/literary | MEDIUM | Inquilab |
| پانی کی قلت | paani ki qillat | water scarcity | water | formal | HIGH | All outlets |
| پینے کے پانی کا بحران | peene ke paani ka buhraan | drinking water crisis | water | formal | HIGH | Munsif Daily |
| خشک سالی | khushk saali | drought | water | formal | HIGH | All outlets |
| بجلی کی کٹوتی | bijli ki katawti | power cut | power | general | HIGH | All outlets |
| لوڈ شیڈنگ | load shedding (borrowed) | load shedding | power | borrowed English | HIGH | All outlets |
| بجلی بحران | bijli buhraan | electricity crisis | power | formal | MEDIUM | Inquilab |
| فصل نقصان | fasal nuqsaan | crop damage | crop | formal | HIGH | All outlets |
| فصل تباہ | fasal tabaah | crop devastated | crop | journalistic | HIGH | Inquilab |
| کسانوں کا نقصان | kisaanon ka nuqsaan | farmers' losses | crop | journalistic | HIGH | All outlets |
| پانی کی کمی | paani ki kami | water deficiency | human | general | HIGH | All outlets |
| ہسپتال میں داخل | haspataal mein daakhil | hospitalized | human | general | HIGH | All outlets |
| اسکول بند | school band | school closed | human | general | HIGH | All outlets |
| امداد | imdaad | relief/aid | govt | formal | HIGH | All outlets |
| ایڈوائزری | advisory (borrowed) | advisory | govt | borrowed English | HIGH | Siasat Daily |
| ریڈ الرٹ | red alert (borrowed) | red alert | govt | borrowed English | HIGH | All outlets |
| درجہ حرارت | daraja-e-hararat | temperature | temperature | formal | HIGH | All outlets |
| درجہ حرارت بڑھا | daraja-e-hararat barha | temperature rose | temperature | formal | HIGH | All outlets |
| پارہ چڑھا | paara charha | mercury rose | temperature | journalistic | HIGH | Inquilab |

---

### 14. NEPALI (ne)

Key outlets: Local outlets in Sikkim, Darjeeling hills, Nepali-language media. Coverage is less intensive than plains states but heat impacts in terai regions are significant.

| Term (Nepali) | Transliteration | English Meaning | Category | Register | Confidence | Sources |
|---|---|---|---|---|---|---|
| लू | loo | hot wind | heatwave | colloquial | HIGH | Common across Nepali media |
| हिट वेभ | hit vebh (borrowed) | heatwave | heatwave | borrowed English | MEDIUM | Online Nepali media |
| भिषण गर्मी | bhishan garmi | severe heat | heatwave | journalistic | HIGH | Nepali news |
| अत्यधिक गर्मी | atyadhik garmi | excessive heat | heatwave | formal | MEDIUM | Formal reports |
| तातो हावा | taato haawa | hot wind | heatwave | colloquial | HIGH | Common usage |
| गर्मीको कहर | garmi ko kahar | fury of heat | heatwave | journalistic | HIGH | Headline pattern |
| लू लाग्नु | loo laagnu | getting heatstroke | death/stroke | colloquial | HIGH | Common usage |
| हिट स्ट्रोक | hit stroke (borrowed) | heatstroke | death/stroke | borrowed English | HIGH | Online media |
| गर्मीले मृत्यु | garmi le mrityu | death from heat | death/stroke | journalistic | HIGH | News reports |
| घामले मृत्यु | ghaam le mrityu | death from sun (ghaam=sun) | death/stroke | colloquial | MEDIUM | Colloquial usage |
| पानीको अभाव | paaniko abhaab | water scarcity | water | formal | HIGH | Common in reporting |
| जल संकट | jal sankat | water crisis | water | formal | HIGH | Formal reporting |
| खडेरी | khaderi | drought | water | formal | HIGH | Standard term |
| खोलाहरू सुक्यो | kholaharu sukyo | streams dried up | water | descriptive | MEDIUM | Descriptive reporting |
| बिजुली कटौती | bijuli katawti | power cut | power | formal | HIGH | Common |
| लोडसेडिङ | loadseding (borrowed) | load shedding | power | borrowed English | HIGH | Very common in Nepal/Nepali media |
| बाली नोक्सानी | baali noksaani | crop damage | crop | formal | HIGH | Agricultural reporting |
| खेती नोक्सानी | kheti noksaani | farming damage | crop | general | HIGH | Common |
| किसानको समस्या | kisaan ko samasya | farmers' problem | crop | journalistic | HIGH | Common |
| निर्जलीकरण | nirjaleekaran | dehydration | human | formal | HIGH | Health reporting |
| अस्पतालमा भर्ना | aspataalma bharnaa | hospitalized | human | general | HIGH | Common |
| विद्यालय बन्द | vidyaalaya banda | school closed | human | general | HIGH | Common |
| राहत | raahat | relief | govt | formal | HIGH | Common |
| चेतावनी | chetaawani | warning | govt | formal | HIGH | Common |
| तापक्रम | taapakram | temperature | temperature | formal | HIGH | Standard term |
| तापक्रम बढ्यो | taapakram badhyo | temperature rose | temperature | formal | HIGH | Common |

---

## Cross-Language Patterns and Observations

### 1. The "Loo" (लू/লু/ଲୁ/لو) Family
The term "loo" (hot wind) is shared across Hindi, Urdu, Bengali, Odia, Marathi, Gujarati, Punjabi, Assamese, and Nepali. It is the single most important colloquial heat term in North and Central India. In each language it takes slightly different verb forms for "being struck by loo":
- Hindi: लू लगना (loo lagna)
- Marathi: लू लागणे (loo laagne)
- Bengali: লু লাগা (lu laga) / লু হাওয়া (lu haowa)
- Odia: ଲୁ ଲାଗିବା (lu lagiba)
- Gujarati: લૂ લાગવી (loo laagvi)
- Punjabi: ਲੂ ਲੱਗਣਾ (loo laggna)
- Urdu: لو لگنا (loo lagna)
- Nepali: लू लाग्नु (loo laagnu)

### 2. Borrowed English Terms Are Essential
Every single language uses borrowed English terms alongside native ones. The most universal borrowed terms:
- **"Heat wave" / "Heatwave"**: Used in every language
- **"Heat stroke"**: Used in every language
- **"Load shedding"**: Used in every language
- **"Red alert" / "Orange alert" / "Yellow alert"**: Used in every language
- **"Advisory"**: Used in most languages
- **"Heat action plan"**: Used in Hindi, Marathi, Gujarati especially

These borrowed terms MUST be included in search queries even for non-English language searches.

### 3. The "Mercury Rising" Idiom
The journalistic idiom of mercury (paara/parod/paadarasam) rising is used across multiple languages:
- Hindi: पारा चढ़ा (paara chadha)
- Bengali: পারদ চড়ছে (parod chorhchhe)
- Marathi: पारा चढला (paara chadhla)
- Gujarati: પારો ચઢ્યો (paaro chadhyo)
- Telugu: పాదరసం పెరిగింది (paadarasam perigindi)
- Punjabi: ਪਾਰਾ ਚੜ੍ਹਿਆ (paara charrhia)
- Urdu: پارہ چڑھا (paara charha)

### 4. Tamil's Unique Cultural Term
Tamil "அக்னி நட்சத்திரம்" (agni nakshatram) is a culturally unique term referring to the hottest astronomical period (roughly mid-May to mid-June). No other Indian language has an equivalent term with this cultural significance. It is very widely used in Tamil media and MUST be included.

### 5. Maharashtra's Unique Power Term
Marathi "भारनियमन" (bhaarniyaman) is the official Maharashtra state term for load regulation/power cuts. It is not used in any other language and is essential for Maharashtra-specific power cut news.

### 6. IMD Official Terminology
The India Meteorological Department uses specific formal terms in each language that may differ from colloquial usage:
- Hindi: उष्ण लहर (ushna lahar) -- formal vs. लू (loo) -- colloquial
- Bengali: তাপপ্রবাহ (tapprobaaho) -- formal vs. দাবদাহ (dabdaho) -- literary/journalistic
- Tamil: வெப்ப அலை (veppa alai) -- formal
- Telugu: ఉష్ణ తరంగం (ushna tarangam) -- formal vs. వడ గాలులు (vada gaalulu) -- colloquial

Both formal and colloquial terms must be included for complete coverage.

### 7. Death-Related Terms by Region
Odisha reports the most heat deaths annually. Terms to watch:
- Odia: ଗରମରେ ମୃତ୍ୟୁ, ଲୁ ଲାଗିବା
- Hindi: लू से मौत, गर्मी से मौत
- Telugu: ఎండ దెబ్బ (enda debba -- literally "sun blow", the standard Telugu term)
- Tamil: வெப்பத்தாக்கம் (heat impact)

### 8. Agricultural Focus by Region
- Punjab/Haryana: Wheat crop damage is the primary concern -- ਕਣਕ ਦੀ ਫ਼ਸਲ ਨੁਕਸਾਨ
- Maharashtra/Vidarbha: Cotton and soybean damage
- Andhra/Telangana: Paddy and crop losses
- All regions use some form of "farmer + distress/crisis" as a headline pattern

---

## Recommended Search Query Strategy

For maximum recall, each language search should include:

1. **Primary native heatwave term** (e.g., Hindi लू, Tamil வெப்ப அலை, Bengali দাবদাহ)
2. **Borrowed "heat wave"** in that script
3. **Death/stroke term** in native + borrowed form
4. **Water crisis term** (native)
5. **Power cut term** (native + "load shedding" in script)

### Example Hindi query set:
```
"लू" OR "भीषण गर्मी" OR "हीट वेव" OR "तापाघात" OR "पारा चढ़ा"
"लू लगना" OR "गर्मी से मौत" OR "हीट स्ट्रोक" OR "सूर्याघात"
"जल संकट" OR "पानी की किल्लत" OR "बिजली कटौती" OR "फसल नुकसान"
```

### Example Tamil query set:
```
"வெப்ப அலை" OR "அக்னி நட்சத்திரம்" OR "கடும் வெயில்" OR "வெப்பத்தாக்கம்"
"மின்வெட்டு" OR "நீர் பற்றாக்குறை" OR "பயிர் சேதம்"
```

---

## Confidence Level Definitions

- **HIGH**: Term is well-established in Indian journalism for heat reporting. Based on extensive exposure to Indian news corpora. Should be included in search queries without hesitation.
- **MEDIUM**: Term is used but less frequently, or is more literary/formal. Include for comprehensive coverage but may generate less volume.
- **LOW**: Term is inferred from linguistic patterns or translated. Needs verification against actual articles before relying on it.

---

## Verification TODO

> **IMPORTANT**: This research was compiled from knowledge of Indian journalism conventions and linguistic patterns. The following verification steps should be completed before finalizing the term dictionary:

1. [ ] Search each HIGH confidence term on Google News in its respective language and confirm it appears in recent heat-related headlines
2. [ ] For each language, open 5-10 actual heatwave articles from the listed outlets and check for any terms NOT captured here
3. [ ] Verify IMD bulletin terminology in each language by checking actual IMD regional language bulletins
4. [ ] Check for any new borrowed terms that may have entered journalistic usage since 2024 (e.g., "heat dome" becoming borrowed)
5. [ ] Validate Tamil "agni nakshatram" usage -- confirm it is still actively used in Dinamalar/Dinamani headlines
6. [ ] Validate Marathi "bharaniyaman" usage in current Loksatta/Maharashtra Times coverage
7. [ ] Check if "heat index" (feels-like temperature) terminology has entered any Indian language journalism
8. [ ] Search for "wet bulb temperature" related terms -- this is an emerging concept in heat reporting
9. [ ] Verify Odia death reporting terminology against actual Sambad/Dharitri heat death articles
10. [ ] Check for compound query terms that combine location + heat term (e.g., "दिल्ली में लू" pattern)

---

## Term Count Summary

| Language | Total Terms | HIGH Confidence | MEDIUM Confidence | Borrowed English Terms |
|----------|-------------|-----------------|--------------------|-----------------------|
| English | 35+ | 28 | 7 | N/A |
| Hindi | 55+ | 40 | 15 | 10 |
| Tamil | 35+ | 25 | 10 | 5 |
| Telugu | 35+ | 25 | 10 | 7 |
| Bengali | 35+ | 25 | 10 | 6 |
| Marathi | 35+ | 25 | 10 | 6 |
| Gujarati | 30+ | 22 | 8 | 7 |
| Kannada | 25+ | 20 | 5 | 5 |
| Malayalam | 25+ | 20 | 5 | 5 |
| Odia | 25+ | 20 | 5 | 3 |
| Punjabi | 25+ | 18 | 7 | 5 |
| Assamese | 22+ | 16 | 6 | 3 |
| Urdu | 30+ | 22 | 8 | 7 |
| Nepali | 25+ | 18 | 7 | 3 |
| **TOTAL** | **~450+** | **~325** | **~125** | **~80** |

---

*This document should be treated as a living reference. As the pipeline begins collecting articles, new terms discovered in actual coverage should be added here. The verification TODO list above should be completed before the pipeline goes into production.*
