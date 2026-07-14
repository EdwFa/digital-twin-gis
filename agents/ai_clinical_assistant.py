import numpy as np

class AIClinicalAssistant:
    """
    Rule-based Псевдо-AI Ассистент.
    Анализирует исторические данные из BloodPool и генерирует
    текстовое клиническое заключение в формате Markdown.
    """
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def generate_report(self):
        history = self.orchestrator.history
        if not history:
            return "Недостаточно данных для анализа."

        report = ["# 🩺 Отчет Клинического AI-Ассистента\n"]
        
        # 1. Анализ Гликемии
        glucose_levels = [state.get("glucose", 5.0) for state in history]
        min_gluc = min(glucose_levels)
        max_gluc = max(glucose_levels)
        
        report.append("## 1. Контроль Гликемии")
        if min_gluc < 3.9:
            report.append(f"⚠️ **КРИТИЧНО:** Зафиксирована гипогликемия (мин. {min_gluc:.1f} ммоль/Л). "
                          "Возможно, доза инсулина превышает потребность, или пациент пропустил прием пищи.")
        elif max_gluc > 11.1:
            report.append(f"⚠️ **ВНИМАНИЕ:** Выраженная гипергликемия (макс. {max_gluc:.1f} ммоль/Л). "
                          "Рекомендуется пересмотреть диету (снизить углеводы) или увеличить базисную терапию.")
        else:
            report.append(f"✅ Уровень глюкозы в норме (диапазон {min_gluc:.1f} - {max_gluc:.1f} ммоль/Л).")

        # 2. Анализ Фармакокинетики (Токсичность)
        report.append("\n## 2. Фармакокинетика и Токсичность")
        drugs = ["paracetamol", "propranolol", "simvastatin"]
        found_drugs = False
        for drug in drugs:
            drug_levels = [state.get(drug, 0.0) for state in history]
            max_drug = max(drug_levels)
            if max_drug > 0.1:
                found_drugs = True
                final_drug = drug_levels[-1]
                clearance_percent = ((max_drug - final_drug) / max_drug) * 100
                report.append(f"- **{drug.capitalize()}**: C_max = {max_drug:.2f} мг/Л. К концу периода выведено {clearance_percent:.1f}% препарата.")
                if clearance_percent < 50.0:
                    report.append(f"  🚨 **ТРЕВОГА:** Замедленная элиминация {drug}. Возможна печеночная недостаточность (Цирроз) или DDI (Лекарственное взаимодействие). Рекомендуется коррекция дозы!")

        if not found_drugs:
            report.append("Лекарственные препараты в крови не обнаружены.")

        # 3. Анализ Метаболизма (Гормоны / Альбумин)
        report.append("\n## 3. Метаболическая панель")
        final_state = history[-1]
        albumin = final_state.get("albumin", 40.0)
        T3 = final_state.get("T3", 2.0)
        
        if albumin < 35.0:
            report.append(f"⚠️ **Гипоальбуминемия** (Альбумин: {albumin:.1f} г/Л). Повышен риск токсичности лекарств из-за высокой свободной фракции (f_u).")
        if T3 < 1.5:
            report.append(f"⚠️ **Гипотиреоз** (T3: {T3:.2f} нмоль/Л). Ожидается общее замедление метаболизма и печеночного клиренса.")

        report.append("\n---\n*Сгенерировано системой Digital Twin (Уровень 0: AI Orchestrator)*")
        return "\n".join(report)
