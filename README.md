# hass-entsoe-qh

Integracja HACS dla Home Assistanta zapewniająca odczyt cen energii elektrycznej z API ENTSO-E w rozdzielczości kwartogodzinnej.

## Funkcje

- Automatyczne pobieranie dokumentu A44 dla bieżącego oraz kolejnego dnia (CET/CEST) co 30 minut.
- Obsługa rozdzielczości PT15M (96 punktów na dobę) i wyliczanie średniej godzinowej.
- Przeliczanie cen z EUR/MWh na wybraną walutę (EUR lub PLN) oraz jednostkę energii (kWh lub MWh).
- Możliwość doliczenia podatku VAT i zastosowania własnego kursu walutowego.
- Udostępnienie dwóch sensorów:
  - `Cena energii 15 min` – aktualna cena w bieżącym przedziale 15-minutowym.
  - `Cena energii 1h` – średnia cena dla bieżącej godziny (cztery punkty kwartogodzinne).
- Atrybuty sensorów zawierają szczegółową listę cen dla dziś i jutra, co umożliwia prezentację prognoz na wykresach.

## Instalacja

1. Dodaj repozytorium do HACS jako niestandardowe.
2. Zainstaluj integrację `ENTSO-E Quarter-Hour`.
3. W Home Assistant przejdź do `Ustawienia → Urządzenia i usługi → Dodaj integrację` i wybierz `ENTSO-E Quarter-Hour`.
4. Podaj token API ENTSO-E oraz skonfiguruj pozostałe parametry (obszar, waluta, kurs walutowy, VAT).

## Konfiguracja

| Pole | Opis |
| ---- | ---- |
| Token API | Klucz bezpieczeństwa uzyskany w portalu ENTSO-E. |
| Kod obszaru (wejście/wyjście) | Domyślnie `10YPL-AREA-----S` dla Polski. |
| Waluta ceny | EUR lub PLN. |
| Jednostka energii | kWh lub MWh. |
| Kurs waluty względem EUR | Wymagany, jeśli wybrano walutę inną niż EUR. |
| Stawka VAT (%) | Opcjonalna stawka podatku doliczana do ceny. |

## Wykresy cen

Atrybuty sensorów zawierają listy danych dla dziś (`prices_today`) oraz jutra (`prices_tomorrow`) w formacie ISO z wartościami liczbowymi. Można je wykorzystać w kartach `statistics-graph`, `apexcharts-card` lub innych rozwiązaniach wizualizacyjnych do prezentacji zarówno historii, jak i prognoz cenowych.

## Licencja

Projekt udostępniany jest na licencji MIT.
