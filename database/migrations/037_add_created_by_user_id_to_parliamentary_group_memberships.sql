-- Add created_by_user_id to parliamentary_group_memberships table for traceability

ALTER TABLE parliamentary_group_memberships
ADD COLUMN created_by_user_id UUID REFERENCES users(user_id);

CREATE INDEX idx_parliamentary_group_memberships_created_by_user_id
ON parliamentary_group_memberships(created_by_user_id);

COMMENT ON COLUMN parliamentary_group_memberships.created_by_user_id IS '議員団メンバーを作成したユーザーID（UUID）';
