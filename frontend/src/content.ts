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
