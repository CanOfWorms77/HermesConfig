---
name: travel-booking
category: productivity
description: Guidelines for helping users research and book travel — what the agent can and cannot do, workflow, and information needed.
---

# Travel Booking Skill

## Capabilities (What I CAN do)

- Search and compare flights, hotels, and packages across booking websites using browser tools
- Find the best prices and deals for specific dates/destinations
- Check availability for flights, hotels, rental cars
- Navigate booking sites and fill in forms with user-provided information
- Put together a shortlist of options for the user to review
- Monitor prices over time (via cron jobs if requested)
- Extract best routes, layover info, baggage allowance details

## Limitations (What I CANNOT do)

- **Make payments** — I should never have or store payment details
- **Provide personal information** — passport numbers, DOB, contact details (user must provide at booking time)
- **Handle CAPTCHAs** — identity verification steps may require user intervention
- **Confirm bookings without final user approval** — always let the user review before hitting "book"
- **Access loyalty accounts** — unless user provides login credentials (generally not recommended)
- **Guarantee prices** — prices can change between search and checkout

## Required Information from User

Before searching, ask for:

1. **Destination** — where to, any flexibility?
2. **Dates** — departure/return, flexible dates?
3. **Travellers** — how many adults, children, ages?
4. **Budget** — per person or total
5. **Departure airport** — nearest/preferred
6. **Preferences** — direct flights only, hotel star rating, specific airlines?
7. **Duration** — how many nights
8. **Trip type** — business, leisure, family, solo

## Workflow

1. Gather requirements (use the list above)
2. Search flights on comparison sites (Google Flights, Skyscanner, Kayak via browser)
3. Search hotels (Booking.com, Hotels.com, Airbnb via browser)
4. Present top 3-5 options with key details (price, times, ratings)
5. User selects preferred option
6. Navigate to booking site and start the reservation process
7. Fill in whatever information user has provided
8. **STOP at payment step** — hand over to user for payment details and final confirmation
9. Offer to set up price monitoring if user isn't ready to book yet

## Pitfalls

- Flight/hotel prices change frequently — note the time of search so user knows how fresh the info is
- Some booking sites have aggressive session timeouts — be prepared to restart searches
- Always double-check dates, airports, and traveller counts before proceeding to booking
- Baggage fees are often not included in initial displayed prices — check the fine print
- Hotel resort fees and taxes may not show until checkout stage
- If a CAPTCHA blocks progress, inform the user they'll need to complete it manually
