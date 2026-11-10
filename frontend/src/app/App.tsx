import { useEffect, useRef } from 'react';
import { Link, NavLink, Route, Routes, useLocation } from 'react-router';
import * as Dialog from '@radix-ui/react-dialog';
import { useQuery } from '@tanstack/react-query';
import { getHealth } from '../shared/api/client';

function Overview() {
  const health = useQuery({
    queryKey: ['service', 'health'],
    queryFn: ({ signal }) => getHealth(signal),
    retry: false,
  });
  return (
    <>
      <p className="eyebrow">VOTRE ESPACE, EN TOUTE CLARTÉ</p>
      <h1>Bienvenue chez vous.</h1>
      <p className="intro">
        Un espace pour organiser vos locations et prendre soin de chaque séjour.
      </p>
      <section className="welcome" aria-labelledby="welcome-title">
        <div className="house" aria-hidden="true">
          ⌂
        </div>
        <h2 id="welcome-title">Tout commence par votre entreprise</h2>
        <p>
          Vos biens, vos séjours et votre équipe seront réunis ici.
          <br />
          L’accès aux comptes sera disponible prochainement.
        </p>
        <Link className="button" to="/guide">
          Découvrir votre espace <span aria-hidden="true">↗</span>
        </Link>
      </section>
      <div className="status" role="status">
        <span className={health.isError ? 'dot warning' : 'dot'} aria-hidden="true" />
        {health.isPending
          ? 'Vérification du service…'
          : health.isError
            ? 'Le service est momentanément indisponible.'
            : 'Connexion au service établie.'}
        {health.isError && <button onClick={() => void health.refetch()}>Réessayer</button>}
      </div>
    </>
  );
}

function Guide() {
  return (
    <>
      <p className="eyebrow">LES ESSENTIELS</p>
      <h1>Un lieu pour tout réunir.</h1>
      <p className="intro">La gestion de vos locations, pensée autour de votre quotidien.</p>
      <div className="guide-grid">
        <article>
          <span aria-hidden="true">01</span>
          <h2>Vos hébergements</h2>
          <p>Regrouper les biens et les unités que votre entreprise propose à la location.</p>
        </article>
        <article>
          <span aria-hidden="true">02</span>
          <h2>Chaque séjour</h2>
          <p>Retrouver les disponibilités, les voyageurs et le suivi des réservations.</p>
        </article>
        <article>
          <span aria-hidden="true">03</span>
          <h2>Votre équipe</h2>
          <p>
            Organiser les interventions et préparer les hébergements pour les prochaines arrivées.
          </p>
        </article>
      </div>
      <p className="note">
        Ces fonctionnalités seront ouvertes progressivement. Aucun bien ni séjour n’est encore
        enregistré dans cet espace.
      </p>
    </>
  );
}

export function App() {
  const location = useLocation();
  const main = useRef<HTMLElement>(null);
  const previous = useRef(location.pathname);
  useEffect(() => {
    if (previous.current !== location.pathname) {
      main.current?.focus();
      previous.current = location.pathname;
    }
  }, [location.pathname]);
  return (
    <div className="layout">
      <a className="skip" href="#main">
        Aller au contenu
      </a>
      <aside className="sidebar">
        <Link to="/" className="brand" aria-label="Property Management, accueil">
          <span aria-hidden="true">⌂</span>
          <span>
            Property
            <br />
            <b>Management</b>
          </span>
        </Link>
        <p className="nav-label">ESPACE DE GESTION</p>
        <nav aria-label="Navigation principale">
          <NavLink end to="/">
            Vue d’ensemble
          </NavLink>
          <NavLink to="/guide">Guide de bienvenue</NavLink>
        </nav>
        <div className="sidebar-bottom">
          <span className="badge">VERSION DÉCOUVERTE</span>
          <p>
            Chaque séjour
            <br />
            commence ici.
          </p>
        </div>
      </aside>
      <div className="workspace">
        <header>
          <span>Votre espace de gestion</span>
          <Dialog.Root>
            <Dialog.Trigger className="about">À propos</Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="overlay" />
              <Dialog.Content className="dialog">
                <Dialog.Title>Property Management</Dialog.Title>
                <Dialog.Description>
                  Votre espace de gestion de locations de courte durée. Version découverte 0.1.0.
                </Dialog.Description>
                <Dialog.Close className="button">Fermer</Dialog.Close>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
        </header>
        <main id="main" ref={main} tabIndex={-1}>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/guide" element={<Guide />} />
            <Route
              path="*"
              element={
                <>
                  <h1>Page introuvable</h1>
                  <Link to="/">Revenir à l’accueil</Link>
                </>
              }
            />
          </Routes>
        </main>
        <footer>
          Property Management <span>Un accueil soigné, une gestion sereine.</span>
        </footer>
      </div>
    </div>
  );
}
