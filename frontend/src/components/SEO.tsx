import { Helmet } from 'react-helmet-async';

interface SEOProps {
  title?: string;
  description?: string;
  keywords?: string;
  url?: string;
  image?: string;
  type?: string;
}

export function SEO({
  title = "Q-Lorify | Infraestrutura Otimizada para Agentes de IA",
  description = "Orquestre fluxos de trabalho de IA poderosos com latência imbatível. Gerencie modelos, monitore o uso e monetize seus agentes de inteligência artificial.",
  keywords = "agentes de IA, infraestrutura LLM, hospedagem de modelos, IA generativa, orquestração de IA, Q-Lorify, Qlorify",
  url = "https://qlorify.com",
  image = "https://qlorify.com/og-image.png",
  type = "website"
}: SEOProps) {
  const fullTitle = title.includes("Q-Lorify") ? title : `${title} | Q-Lorify`;

  return (
    <Helmet>
      {/* Primary Meta Tags */}
      <title>{fullTitle}</title>
      <meta name="title" content={fullTitle} />
      <meta name="description" content={description} />
      <meta name="keywords" content={keywords} />
      <link rel="canonical" href={url} />

      {/* Open Graph / Facebook */}
      <meta property="og:type" content={type} />
      <meta property="og:url" content={url} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={image} />

      {/* Twitter */}
      <meta property="twitter:card" content="summary_large_image" />
      <meta property="twitter:url" content={url} />
      <meta property="twitter:title" content={fullTitle} />
      <meta property="twitter:description" content={description} />
      <meta property="twitter:image" content={image} />
    </Helmet>
  );
}
