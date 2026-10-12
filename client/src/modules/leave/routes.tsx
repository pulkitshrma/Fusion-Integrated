import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const LeaveInboxPage = lazy(() => import("./pages/LeaveInboxPage"));
const LeaveAdminPage = lazy(() => import("./pages/LeaveAdminPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "inbox", element: <LeaveInboxPage /> },
  { path: "admin", element: <LeaveAdminPage /> },
];
