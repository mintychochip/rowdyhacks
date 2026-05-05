import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useMediaQuery } from '../hooks/useMediaQuery';
import * as api from '../services/api';
import MarkdownRenderer from '../components/MarkdownRenderer';
import {
  PRIMARY, CYAN, SUCCESS, WARNING, ERROR,
  TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_WHITE,
  CARD_BG, INPUT_BG, INPUT_BORDER, BORDER,
  TYPO, SPACE, RADIUS,
} from '../theme';

interface ContentPage {
  id: string;
  slug: string;
  title: string;
  content: string;
  tab_group: string;
  sort_order: number;
  tab_group_order: number;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export default function ContentEditorPage() {
  return <div>Content Editor Page</div>;
}
