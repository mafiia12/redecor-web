// Team shown on the About page. Titles come from the company profile (Brief, page 4), where the
// layout was ambiguous: set SHOW_TEAM to true only after the titles below are confirmed.
export const SHOW_TEAM = false;

export interface Member {
  name: { en: string; ar: string };
  title: { en: string; ar: string };
}

export const TEAM: Member[] = [
  { name: { en: "Eng. Gamal Eissa", ar: "م. جمال عيسى" }, title: { en: "Chief Executive Officer", ar: "الرئيس التنفيذي" } },
  { name: { en: "Eng. Mohamed Hussien", ar: "م. محمد حسين" }, title: { en: "Chief Design Officer", ar: "رئيس قطاع التصميم" } },
  { name: { en: "Eng. Ahmed Elkafrawy", ar: "م. أحمد الكفراوي" }, title: { en: "Commercial Director", ar: "المدير التجاري" } },
  { name: { en: "Eng. Ahmed Essam", ar: "م. أحمد عصام" }, title: { en: "Business Developer Manager", ar: "مدير تطوير الأعمال" } },
];
