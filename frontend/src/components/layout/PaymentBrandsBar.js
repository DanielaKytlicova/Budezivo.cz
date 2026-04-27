import React from 'react';

/**
 * PaymentBrandsBar — povinný blok pro schválení Comgate.
 *
 * Loga: Comgate, Visa, Mastercard. Inline SVG, aby se neumísťovaly externí závislosti
 * a barvy odpovídaly oficiálním brand guidelines.
 *
 * Reference: https://help.comgate.cz/docs/cs/loga-a-udaje-na-webu
 */
export const PaymentBrandsBar = () => {
  return (
    <div
      className="flex flex-wrap items-center justify-center md:justify-start gap-x-6 gap-y-3"
      data-testid="payment-brands-bar"
      aria-label="Akceptované platební metody a poskytovatel platební brány"
    >
      {/* Comgate logo */}
      <a
        href="https://www.comgate.eu/cs/platebni-brana"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center bg-white rounded-md px-3 py-1.5 shadow-sm hover:shadow-md transition-shadow"
        aria-label="Comgate — platební brána"
        data-testid="brand-comgate"
        title="Platební brána Comgate"
      >
        <svg width="98" height="22" viewBox="0 0 200 44" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          {/* Mark — gradient curved C */}
          <defs>
            <linearGradient id="cg-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#FF7A00" />
              <stop offset="100%" stopColor="#FF3366" />
            </linearGradient>
          </defs>
          <path
            d="M22 4 A18 18 0 1 0 22 40 L22 32 A10 10 0 1 1 22 12 Z"
            fill="url(#cg-grad)"
          />
          {/* Wordmark */}
          <text
            x="50"
            y="28"
            fontFamily="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
            fontSize="20"
            fontWeight="700"
            fill="#1A1A2E"
            letterSpacing="-0.5"
          >
            comgate
          </text>
        </svg>
      </a>

      {/* Visa */}
      <div
        className="flex items-center bg-white rounded-md px-3 py-1.5 shadow-sm"
        data-testid="brand-visa"
        title="Visa"
        aria-label="Visa"
      >
        <svg width="50" height="18" viewBox="0 0 100 36" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <text
            x="50"
            y="27"
            textAnchor="middle"
            fontFamily="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, sans-serif"
            fontSize="26"
            fontWeight="900"
            fill="#1A1F71"
            fontStyle="italic"
            letterSpacing="-1"
          >
            VISA
          </text>
        </svg>
      </div>

      {/* Mastercard */}
      <div
        className="flex items-center bg-white rounded-md px-3 py-1.5 shadow-sm"
        data-testid="brand-mastercard"
        title="Mastercard"
        aria-label="Mastercard"
      >
        <svg width="42" height="26" viewBox="0 0 60 36" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <circle cx="22" cy="18" r="13" fill="#EB001B" />
          <circle cx="38" cy="18" r="13" fill="#F79E1B" />
          {/* overlap area in proper Mastercard orange */}
          <path
            d="M30 8 a13 13 0 0 1 0 20 a13 13 0 0 1 0 -20"
            fill="#FF5F00"
          />
        </svg>
      </div>
    </div>
  );
};

export default PaymentBrandsBar;
