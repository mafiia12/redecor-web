// Team shown on the About page (titles confirmed by the client).
export const SHOW_TEAM = true;

export interface Member {
  name: { en: string; ar: string };
  title: { en: string; ar: string };
}

export const TEAM: Member[] = [
  { name: { en: "Eng. Mohamed Hussien", ar: "م. محمد حسين" }, title: { en: "Chief Executive Officer", ar: "الرئيس التنفيذي" } },
  { name: { en: "Eng. Gamal Eissa", ar: "م. جمال عيسى" }, title: { en: "Chief Design Officer", ar: "رئيس قطاع التصميم" } },
  { name: { en: "Eng. Ahmed Essam", ar: "م. أحمد عصام" }, title: { en: "Commercial Director", ar: "المدير التجاري" } },
  { name: { en: "Eng. Ahmed Elkafrawy", ar: "م. أحمد الكفراوي" }, title: { en: "Business Developer Manager", ar: "مدير تطوير الأعمال" } },
];

export interface Division {
  id: string;
  name: { en: string; ar: string };
  text: { en: string; ar: string };
  points: { en: string[]; ar: string[] };
  /** Names (TEAM[].name.en) of the people who lead this division. */
  lead: string[];
}

// Draft wording based on the company profile; edit freely.
export const DIVISIONS: Division[] = [
  {
    id: "design",
    name: { en: "Interior Design", ar: "التصميم الداخلي" },
    text: {
      en: "Architectural and interior design that turns an idea into a clear, buildable concept: layouts, materials, lighting and furniture, presented in 3D before anything is built.",
      ar: "تصميم معماري وداخلي يحوّل الفكرة إلى مفهوم واضح قابل للتنفيذ: توزيع وخامات وإضاءة وأثاث، مع عرض ثلاثي الأبعاد قبل أي تنفيذ.",
    },
    points: {
      en: ["Concept and design development", "3D visualization", "Material and furniture boards", "Shop drawings"],
      ar: ["فكرة التصميم وتطويره", "التصور ثلاثي الأبعاد", "لوحات الخامات والأثاث", "رسومات التنفيذ"],
    },
    lead: ["Eng. Gamal Eissa"],
  },
  {
    id: "execution",
    name: { en: "Execution & Fit-Out", ar: "التنفيذ والتشطيبات" },
    text: {
      en: "Our site teams deliver finishing and fit-out works to the approved drawings, with technical coordination on site and a clean handover.",
      ar: "فرق الموقع لدينا تنفّذ أعمال التشطيب والتجهيز وفق الرسومات المعتمدة، مع التنسيق الفني في الموقع وتسليم منظّم.",
    },
    points: {
      en: ["Fit-out and finishing works", "Technical coordination", "Site supervision", "Handover and close-out"],
      ar: ["أعمال التشطيب والتجهيز", "التنسيق الفني", "الإشراف في الموقع", "التسليم والإغلاق"],
    },
    lead: [],
  },
  {
    id: "contracting",
    name: { en: "Contracting & Commercial", ar: "التعاقدات والتجاري" },
    text: {
      en: "Pricing, procurement and contracts handled in one place, so the budget, the supply plan and the programme stay aligned.",
      ar: "التسعير والمشتريات والتعاقدات في مكان واحد، لتبقى الميزانية وخطة التوريد والجدول الزمني على نفس الخط.",
    },
    points: {
      en: ["Tender pricing and BOQ", "Procurement and supply", "Subcontracts", "Cost control"],
      ar: ["تسعير المناقصات والمقايسات", "المشتريات والتوريد", "عقود المقاولين", "التحكم في التكلفة"],
    },
    lead: ["Eng. Ahmed Essam"],
  },
  {
    id: "bd",
    name: { en: "Business Development", ar: "تطوير الأعمال" },
    text: {
      en: "We build long-term relationships with developers, operators and brands, and shape each proposal around the client’s real needs.",
      ar: "نبني علاقات طويلة المدى مع المطورين والمشغّلين والعلامات التجارية، ونصيغ كل عرض حول احتياج العميل الفعلي.",
    },
    points: {
      en: ["Client proposals", "Partnerships", "Market development", "New services"],
      ar: ["عروض العملاء", "الشراكات", "تطوير السوق", "خدمات جديدة"],
    },
    lead: ["Eng. Ahmed Elkafrawy"],
  },
];

/** About-page figures, in the order of t.about.stats. Only figures the company has confirmed are shown.
 *  "3 regional bases" waits for confirmation (two offices are listed today): set it to true once confirmed. */
export const STAT_CONFIRMED: boolean[] = [true, true, false];
